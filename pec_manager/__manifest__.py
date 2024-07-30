{
    "name": "PEC Manager (in Helpdesk)",
    "version": "0.70",
    "category": "Services/Helpdesk",
    "summary": "Manage PEC messages in Helpdesk App",
    "website": "https://github.com/madgrog/pec_manager",
    # optional dependance: "mail_debrand" from OCA/social
    "depends": ["mail", "helpdesk", "l10n_it_pec", "contacts", "hr"],
    "data": [
        'security/pec_manager_security.xml',
        'security/ir.model.access.csv',
        "data/mail_template_data.xml",
        "views/fetchmail_views.xml",
        "views/helpdesk_views.xml",
        "views/helpdesk_team_views.xml",
        "views/mail_alias_views.xml",
        # "wizard/mail_compose_message_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "pec_manager/static/src/js/**/*.js",
        ],
    },
    "application": True,
    "license": "AGPL-3",
    "author": "Luigi Lamorte",
}
