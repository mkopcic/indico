# This file is part of Indico.
# Copyright (C) 2002 - 2020 CERN
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see the
# LICENSE file for more details.

import hashlib

import pytest

from indico.util.passwords import BCryptPassword, PasswordProperty


def md5(s):
    if isinstance(s, str):
        s = s.encode()
    return hashlib.md5(s).hexdigest()


class Foo:
    def __init__(self, password=None):
        if password is not None:
            self.password = password

    password = PasswordProperty('_password')


@pytest.fixture
def mock_bcrypt(mocker):
    def _hashpw(value, salt):
        assert isinstance(value, bytes), 'hashpw expects bytes'
        assert isinstance(salt, bytes), 'hashpw expects bytes'
        return md5(value)

    bcrypt = mocker.patch('indico.util.passwords.bcrypt')
    bcrypt.gensalt.return_value = b'salt'
    bcrypt.hashpw.side_effect = _hashpw
    bcrypt.checkpw = lambda pwd, pwdhash: md5(pwd) == pwdhash
    return bcrypt


def test_passwordproperty_get_class(mock_bcrypt):
    assert isinstance(Foo.password, PasswordProperty)
    assert Foo.password.backend.hash('test') == '098f6bcd4621d373cade4e832627b4f6'
    assert mock_bcrypt.hashpw.called
    mock_bcrypt.hashpw.assert_called_with(b'test', b'salt')


@pytest.mark.parametrize('password', ('m\xf6p', 'foo'))
def test_passwordproperty_set(mock_bcrypt, password):
    test = Foo()
    test.password = password
    assert mock_bcrypt.hashpw.called
    mock_bcrypt.hashpw.assert_called_with(password.encode(), b'salt')
    assert test._password == md5(password)


@pytest.mark.parametrize('password', ('', None))
@pytest.mark.usefixtures('mock_bcrypt')
def test_passwordproperty_set_invalid(password):
    test = Foo()
    with pytest.raises(ValueError):
        test.password = password


@pytest.mark.usefixtures('mock_bcrypt')
def test_passwordproperty_del():
    test = Foo()
    test.password = 'foo'
    assert test._password == md5('foo')
    del test.password
    assert test._password is None


def test_passwordproperty_get():
    test = Foo()
    assert isinstance(test.password, BCryptPassword)


@pytest.mark.parametrize('password', ('moep', 'm\xf6p'))
@pytest.mark.usefixtures('mock_bcrypt')
def test_bcryptpassword_check(password):
    password_hash = md5(password)
    pw = BCryptPassword(password_hash)
    assert pw == password
    assert pw != 'notthepassword'


@pytest.mark.usefixtures('mock_bcrypt')
def test_bcryptpassword_fail_bytes():
    pw = BCryptPassword(md5('foo'))
    with pytest.raises(TypeError) as exc_info:
        pw == b'foo'
    assert str(exc_info.value) == "password must be str, not <class 'bytes'>"


@pytest.mark.parametrize(('password_hash', 'password'), (
    (md5(b''), ''),
    ('', ''),
    ('', 'foo'),
    ('foo', '')
))
@pytest.mark.usefixtures('mock_bcrypt')
def test_bcryptpassword_check_empty(password_hash, password):
    pw = Foo().password
    pw.hash = password_hash
    assert pw != 'xxx'
    assert pw != password
