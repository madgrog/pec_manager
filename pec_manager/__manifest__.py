{
    "name": "PEC Manager (in Helpdesk)",
    "version": "0.60",
    "category": "Services/Helpdesk",
    "summary": "Manage PEC messages in Helpdesk App",
    "website": "https://github.com/madgrog",
    "depends": ["mail", "helpdesk", "l10n_it_pec", "contacts"],
    "data": [
        "data/mail_template_data.xml",
        "views/fetchmail_views.xml",
        "views/helpdesk_views.xml",
        "views/helpdesk_team_views.xml",
        "views/mail_alias_views.xml",
    ],
    'assets': {
        'mail.assets_messaging': [
            'mail/static/src/models/*.js',
        ],
    },
    "application": True,
    "license": "AGPL-3",
    "author": "Luigi Lamorte",
}
