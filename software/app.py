from flask import Flask, request, url_for, redirect
from flask.ext.sqlalchemy import SQLAlchemy
from sandman import app as sandman_app
from sandman.model import activate, register, Model
from werkzeug.wsgi import DispatcherMiddleware
from werkzeug.serving import run_simple
from werkzeug.debug import DebuggedApplication

import datetime
import hashlib
import math
import os
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.getcwd() + '/venv/test.db'
app.debug = True
db = SQLAlchemy(app)

sandman_app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI']
sandman_app.debug = True

class AclUserList(db.Model):
    __tablename__ = "acluserlist"
    __endpoint__= "acluserlist"
    __methods__ = ('GET', 'POST', 'PATCH', 'PUT', 'DELETE')

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    acls_id = db.Column(db.Integer, db.ForeignKey('acls.id'))

class AclUserListApi(Model):
    __tablename__ = "acluserlist"
    __endpoint__= "acluserlist"
    __methods__ = ('GET', 'POST', 'PATCH', 'PUT', 'DELETE')

class User(db.Model):
    __tablename__ = "user"
    __endpoint__= "users"
    __methods__ = ('GET', 'POST', 'PATCH', 'PUT', 'DELETE')

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    username = db.Column(db.String(100))
    keys = db.relationship('RfidKey', backref='User', lazy='dynamic')
    name = db.Column(db.String(100))
    acls_registered = db.relationship('AclUserList',
                        backref='User',
                        lazy='dynamic')
    accessExpires = db.Column(db.DateTime)

    def __repr__(self):
        return 'User: %s' % username

class UserApi(Model):
    __tablename__ = "user"
    __endpoint__= "users"
    __methods__ = ('GET', 'POST', 'PATCH', 'PUT', 'DELETE')


class RfidKey(db.Model):
  __tablename__ = "rfid_key"
  __endpoint__ = "rfids"
  __methods__ = ('GET', 'POST', 'PATCH', 'PUT', 'DELETE')

  id = db.Column(db.Integer, primary_key=True,nullable=False)
  rfidKey = db.Column(db.String(40))
  hashedPass = db.Column(db.String(128))
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

  def hashPin(self,pin):
    return hashlib.sha512(pin).hexdigest()

  def __repr__(self):
    return '<Rfid %r>' % self.rfidKey

class RfidKeyApi(Model):
    __tablename__ = "rfid_key"
    __endpoint__ = "rfids"
    __methods__ = ('GET', 'POST', 'PATCH', 'PUT', 'DELETE')

class AccessControlList(db.Model):
    __tablename__ = "acls"
    __endpoint__ = "acls"
    __methods__ = ('GET', 'POST', 'PATCH', 'PUT', 'DELETE')

    id = db.Column(db.Integer, primary_key = True, nullable=False)
    description = db.Column(db.String(128))
    user_ids = db.relationship("AclUserList",
                        backref="acls", lazy='dynamic')
    lastEdited = db.Column(db.Integer)

    def __repr__(self):
        return description[:80]
class AccessControlListApi(Model):
    __tablename__ = "acls"
    __endpoint__ = "acls"
    __methods__ = ('GET', 'POST', 'PATCH', 'PUT', 'DELETE')


class Unit(db.Model):
    __tablename__ = "accessunits"
    __endpoint__ = "accessunits"
    __methods__ = ('GET', 'POST', 'PATCH', 'PUT', 'DELETE')

    id = db.Column(db.Integer, primary_key = True, nullable=False)
    description = db.Column(db.String(100))
    lastPinged = db.Column(db.Integer)
    acl_id = db.Column(db.Integer, db.ForeignKey("acls.id"))

    def __repr__(self):
        return description[:80]
class UnitApi(Model):
    __tablename__ = "accessunits"
    __endpoint__ = "accessunits"
    __methods__ = ('GET', 'POST', 'PATCH', 'PUT', 'DELETE')

class Log(db.Model):
    __tablename__ = "logs"
    __endpoint__ = "logs"
    __methods__ = ('GET', 'POST', 'PATCH', 'PUT', 'DELETE')

    id = db.Column(db.Integer, primary_key = True, nullable = False)
    description = db.Column(db.String(256))
    savedOn = db.Column(db.DateTime)

    def __repr__(self):
        return description[:80]
class LogApi(Model):
    __tablename__ = "logs"
    __endpoint__ = "logs"
    __methods__ = ('GET', 'POST', 'PATCH', 'PUT', 'DELETE')

def getUTCnow():
    return int(math.floor(time.time()))

def getUTCtimeFromDateTime(dt):
    epoch = datetime.datetime(1970,1,1)
    return int(math.floor((dt-epoch).total_seconds()))

@app.route('/')
def index():
  return "Nothing to see here"

@app.route('/ping')
def setupNewUnit():
    newUnit = Unit()
    db.session.add(newUnit)
    db.session.commit()
    return str(newUnit.id)

@app.route('/ping/<int:unitID>/<int:curUnitTime>/<int:lastUnitAclUpdate>')
def respondToUnitPing(unitID,curUnitTime,lastUnitAclUpdate):
    error = 0; # 10=noUnit, 20=noACLSet
    retCode = 0; #1=updateTime, 2 = updateAcl
    unit = Unit.query.filter_by(id=unitID).first()
    curTime = getUTCnow()

    if unit:
        if curTime - curUnitTime > 10:
            retCode += 1;

        acl = AccessControlList.query.filter_by(id=unit.acl_id).first()
        if acl:
            if acl.lastEdited > lastUnitAclUpdate:
                retCode += 2;
        else:
            error += 20;
    else:
        error += 10;

    return str(error + retCode)

#return seconds since epoch in UTC
@app.route('/time')
def currentTime():
    return str(getUTCnow())

@app.route('/getACL/<int:unitId>')
def getACL(unitId):
    retTable = [] #rows of data, each row being rfidKeyStr,16 bit 5 digit dateExpires
    unit = Unit.query.filter_by(id=unitId).first()
    if unit:
        acl = AccessControlList.query.filter_by(id=unit.acl_id).first()
        if acl:
            for aclRow in acl.user_ids.filter_by(acls_id=acl.id).all():
                row = ''
                userObj = User.query.filter_by(id=aclRow.user_id).first()
                timeSinceEpoch = getUTCtimeFromDateTime(userObj.accessExpires)
                setTime = int(math.floor(timeSinceEpoch/100000))
                for key in userObj.keys:
                    row = '%s,%s' % (key.rfidKey,setTime)
                    retTable.append(row)
    return '\n'.join(retTable)

@app.route('/checkPw/<rfidkey>', methods=['GET', 'POST'])
def checkPw(rfidkey):
    retCode = 0; # 0 = no match, 1 = match
    error = 0; # 10 = noMatchingRfid, 20 = NoPinSent
    rfid = RfidKey.query.filter_by(rfidKey=rfidkey).first()
    if rfid:
        if request.form['pin'] != None:
            if rfid.hashedPass == rfid.hashPin(request.form['pin']):
                retCode = 1;
        else:
            error += 20;

    else:
        error += 10;

    return str(error + retCode)

if __name__ == "__main__":

  register((RfidKeyApi,UserApi,AccessControlListApi,UnitApi,LogApi,AclUserListApi))
  activate(browser=False)

  application = DispatcherMiddleware(app, {
    '/api': sandman_app,
    })

  debugged_app = DebuggedApplication(application, evalex=True)

  run_simple('0.0.0.0', 8080, debugged_app, use_reloader=True, use_debugger=True, use_evalex=True)
