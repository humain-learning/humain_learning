app_name = "humain_learning"
app_title = "Humain Learning"
app_publisher = "Raghav Kaul"
app_description = "Customizations for Humain Learning"
app_email = "raghav.kaul@humainlearning.ai"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "humain_learning",
# 		"logo": "/assets/humain_learning/logo.png",
# 		"title": "Humain Learning",
# 		"route": "/humain_learning",
# 		"has_permission": "humain_learning.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/humain_learning/css/humain_learning.css"
# app_include_js = "/assets/humain_learning/js/humain_learning.js"

# include js, css files in header of web template
# web_include_css = "/assets/humain_learning/css/humain_learning.css"
# web_include_js = "/assets/humain_learning/js/humain_learning.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "humain_learning/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "humain_learning/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "humain_learning.utils.jinja_methods",
# 	"filters": "humain_learning.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "humain_learning.install.before_install"
# after_install = "humain_learning.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "humain_learning.uninstall.before_uninstall"
# after_uninstall = "humain_learning.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "humain_learning.utils.before_app_install"
# after_app_install = "humain_learning.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "humain_learning.utils.before_app_uninstall"
# after_app_uninstall = "humain_learning.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "humain_learning.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "CRM Lead": {
        "before_insert": [
            "humain_learning.humain_learning.lead_controller.assign_campaign",
            "humain_learning.humain_learning.lead_controller.standardize_mobile",
            ],
        "after_insert": [
            "humain_learning.zoom_autoregistration.lead_hooks.register_lead_to_webinar"
            ]
    }
}

doctype_list_js = {
    "Failed Registration": "humain_learning.public/js/failed_registration_list.js"
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"humain_learning.tasks.all"
# 	],
# 	"daily": [
# 		"humain_learning.tasks.daily"
# 	],
# 	"hourly": [
# 		"humain_learning.tasks.hourly"
# 	],
# 	"weekly": [
# 		"humain_learning.tasks.weekly"
# 	],
# 	"monthly": [
# 		"humain_learning.tasks.monthly"
# 	],
# }
scheduler_events = {
    "cron": {
        "*/30 * * * *": [
            "humain_learning.zoom_autoregistration.oauth.auth.refresh_token"
        ]
    }
}

fixtures = [
    "Custom Field",
    "Property Setter"
]
# Testing
# -------

# before_tests = "humain_learning.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "humain_learning.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "humain_learning.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["humain_learning.utils.before_request"]
# after_request = ["humain_learning.utils.after_request"]

# Job Events
# ----------
# before_job = ["humain_learning.utils.before_job"]
# after_job = ["humain_learning.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"humain_learning.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

