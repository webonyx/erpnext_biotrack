from __future__ import unicode_literals
from .client import post

def call(fn, *args, **kwargs):
	return post(fn, *args, **kwargs)