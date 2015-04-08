from flask import Flask, request, url_for, redirect
from flask.ext.sqlalchemy import SQLAlchemy
from sandman import app as sandman_app
from sandman.model import activate, register, Model
from werkzeug.wsgi import DispatcherMiddleware
from werkzeug.serving import run_simple
from werkzeug.debug import DebuggedApplication

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

class User(db.Model):
    __tablename__ = "user"
    __endpoint__= "users"

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    username = db.Column(db.String(100))
    keys = db.relationship('RfidKey', backref='User', lazy='dynamic')
    name = db.Column(db.String(100))

    def __init__(self, username, name=None):
        self.username = username
        if name:
            self.name = name

    def __repr__(self):
        return 'User: %s' % username

class RfidKey(db.Model):
  __tablename__ = "rfid_key"
  __endpoint__ = "rfids"

  id = db.Column(db.Integer, primary_key=True,nullable=False)
  rfidKey = db.Column(db.String(40))
  hashedPass = db.Column(db.String(128))
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

  def __init__(self, rfidKey, pin = None):
    self.rfidKey = rfidKey
    self.hashedPass = ''
    if pin:
        self.hashedPass = self.hashPin(pin)

  def hashPin(pin):
    return hashlib.sha512(pin).hexdigest

  def __repr__(self):
    return '<Rfid %r>' % self.rfidKey

aclData = db.Table('aclData',
    db.Column("user_id",db.Integer, db.ForeignKey('user.id')),
    db.Column("acl_id", db.Integer, db.ForeignKey('acls.id'))
    )

class AccessControlList(db.Model):
    __tablename__ = "acls"
    __endpoint__ = "acls"

    id = db.Column(db.Integer, primary_key = True, nullable=False)
    description = db.Column(db.String(128))
    user_ids = db.relationship("User", secondary=aclData , backref=db.backref("acls", lazy='dynamic'))
    lastEdited = db.Column(db.Integer)

    def __init__(self,description):
        self.description = description

class Unit(db.Model):
    __tablename__ = "accessunits"
    __endpoint__ = "accessunits"

    id = db.Column(db.Integer, primary_key = True, nullable=False)
    description = db.Column(db.String(100))
    lastPinged = db.Column(db.Integer)
    acl_id = db.Column(db.Integer, db.ForeignKey("acls.id"))

    def __init__(self):
        self.lastPinged = 0

def getUTCnow():
    return int(math.floor(time.time()))

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


@app.route('/getACL/<int:ACLId>')
def getACL(ACLId):
    return 0            #TODO

@app.route('/checkPw/<rfidkey>')
def checkPw(rfidkey):
    retCode = 0; # 0 = no match, 1 = match
    error = 0; # 10 = noMatchingRfid, 20 = NoPinSent
    rfid = RfidKey.query.filter_by(rfidKey=rfidkey).first()
    if rfid:
        if request.form['pin'] != None:
            if rfid.hashedPass == RfidKey.hashPin(request.form['pin']):
                retCode = 1;
        else:
            error += 20;

    else:
        error += 10;

    return str(error + retCode)

if __name__ == "__main__":

  register((RfidKey,User,AccessControlList,Unit))
  activate(browser=False)

  application = DispatcherMiddleware(app, {
    '/api': sandman_app,
    })

  debugged_app = DebuggedApplication(application, evalex=True)

  run_simple('0.0.0.0', 8080, debugged_app, use_reloader=True, use_debugger=True, use_evalex=True)
