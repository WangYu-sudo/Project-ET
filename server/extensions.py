# -*- coding: utf-8 -*-
"""
Flask 扩展集中初始化
"""
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()


def init_extensions(app):
    db.init_app(app)
    bcrypt.init_app(app)
