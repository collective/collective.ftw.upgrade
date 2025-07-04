from collective.ftw.upgrade.command.jsonapi import add_requestor_authentication_argument
from collective.ftw.upgrade.command.jsonapi import add_requestor_instance_argument
from collective.ftw.upgrade.command.jsonapi import error_handling
from collective.ftw.upgrade.command.jsonapi import with_api_requestor
from collective.ftw.upgrade.command.terminal import TERMINAL


DOCS = """
{t.bold}DESCRIPTION:{t.normal}
    Test authentication, printing the user you are authenticated with.

{t.bold}EXAMPLES:{t.normal}
[quote]
    $ bin/upgrade user --auth admin:admin
    Authenticated as "admin".
[/quote]
""".format(
    t=TERMINAL
).strip()


def setup_argparser(commands):
    command = commands.add_parser(
        "user", help="Test authentication and print user.", description=DOCS
    )
    command.set_defaults(func=sites_command)
    add_requestor_authentication_argument(command)
    add_requestor_instance_argument(command)


@with_api_requestor
@error_handling
def sites_command(args, requestor):
    response = requestor.GET("current_user")
    print(f'Authenticated as "{response.json()}".')
