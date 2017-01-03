"""
Configuration for docs
"""

source_link = "https://github.com/webonyx/erpnext_biotrack"
docs_base_url = "https://webonyx.github.io/erpnext_biotrack"
headline = "Traceability"
sub_heading = "Traceability System"
long_description = """ A very long description """

docs_version = "1.x.x"
splash_light_background = True

# source_link = "https://github.com/[org_name]/erpnext_biotrack"
# docs_base_url = "https://[org_name].github.io/erpnext_biotrack"
# headline = "App that does everything"
# sub_heading = "Yes, you got that right the first time, everything"

def get_context(context):
	context.brand_html = "Traceability"
	context.app.splash_light_background = True
