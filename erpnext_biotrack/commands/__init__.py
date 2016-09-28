# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals, absolute_import
import os, click, subprocess
import frappe
from frappe.migrate import migrate
from frappe.commands import pass_context, get_site


@click.command('update')
@pass_context
def update(context):
	app = __name__.split('.')[0]
	app_dir = os.path.join('.', '../apps', app)

	if os.path.exists(os.path.join(app_dir, '.git')):
		print "Pulling app..."
		s = subprocess.Popen(['git', 'pull'], cwd=app_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		out = s.stdout.read()
		s.stdout.close()
		print out

	site = get_site(context)
	frappe.init(site=site)
	frappe.connect()
	migrate()
	frappe.destroy()


@click.command('set-training-mode')
@click.option('--site', help='site name')
@click.argument('state', type=click.Choice(['on', 'off']))
@pass_context
def set_training_mode(context, state, site=None):
	if not site:
		site = get_site(context)

	try:
		frappe.init(site=site)
		frappe.connect()
		frappe.db.set_value("BioTrack Settings", None, "is_training", 1 if (state == 'on') else 0)
		frappe.db.commit()
		print "Training mode set for site {}".format(site)
	finally:
		frappe.destroy()


commands = [
	update,
	set_training_mode,
]
