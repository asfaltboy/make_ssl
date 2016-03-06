"""
This helper script simplifies the LetsEncrypt SSL setup process.

It uses `simp_le` to obtain certs, assumes nginx and uses requests to verify
nginx config. It will output a step-by-step guide to follow, not daring to
write nginx configuration on it's own.

This script is to be distributed with PEX, run `make <linux/osx>` to build it.

Bash auto-completion is availably; put the following in your `.bashrc`:

    eval "$(_MAKE_SSL_OSX_COMPLETE=source /path/to/make-ssl-osx)"    # or
    eval "$(_MAKE_SSL_OSX_COMPLETE=source /path/to/make-ssl-linux)"
"""
from distutils.spawn import find_executable
import logging
import os
import sys

# why the pylint comment? see https://github.com/PyCQA/pylint/issues/464
from builtins import input  # pylint: disable=redefined-builtin
import click
import requests
import simp_le

logging.basicConfig()

HOME_DIR = os.path.expanduser('~')
LE_BASE = os.path.join(HOME_DIR, 'letsencrypt')
CERTS_DIR = os.path.join(LE_BASE, 'certs')
CHALLENGE_DIR = os.path.join(LE_BASE, 'challenge')
SIMP_LE = find_executable('simp_le') or '%s simp_le' % sys.argv[0]

NGINX_CHALLENGE = """
### add to server listening to port 80 section ###
    location '/.well-known/acme-challenge' {{
        default_type "text/plain";
        root         {challenge_dir};
    }}
""".format(challenge_dir=CHALLENGE_DIR)

NGINX_SSL = """
### add to server listening to port 443 section ###
    ssl_certificate      {certs_dir}/fullchain.pem;
    ssl_certificate_key  {certs_dir}/key.pem;

    add_header Strict-Transport-Security max-age=15768000;
    ssl_session_timeout  5m;
    ssl_protocols     TLSv1.2 TLSv1.1 TLSv1;
    ssl_session_cache shared:SSL:10m;
    ssl_ciphers 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:DHE-RSA-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:CAMELLIA:DES-CBC3-SHA:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA';
    ssl_prefer_server_ciphers on;
""".format(certs_dir=CERTS_DIR)

SIMP_LE_ARGS = ['-f', 'fullchain.pem', '-f', 'key.pem']
SIMP_LE_TMPL = """!#/bin/bash
cd {certs_dir}
{executable} %s
""".format(executable=SIMP_LE, certs_dir=CERTS_DIR)

DOMAIN_PART_TMPL = "  -d %s:{challenge_dir}".format(challenge_dir=CHALLENGE_DIR)


def get_nginx_files(conf_dir, skip_modified=False):
    """ Return the files in nginx conf.d dir, optionally skipping those which
    have already been modified to include the `acme-challenge` """
    assert os.path.exists(conf_dir), (
        'Could not locate nginx conf dir at %s. Please provide correct '
        'location or set env var NGINX_CONF=<correct_dir>' % conf_dir)
    file_list = []
    for conf_path in os.listdir(conf_dir):
        fpath = os.path.join(conf_dir, conf_path)
        if skip_modified:
            with open(fpath) as conf_file:
                if '/.well-known/acme-challenge' in conf_file.read():
                    click.echo('Already found acme-challenge in %s, skipping' % conf_path)
                    continue
            click.echo('File %s requires acme-challenge' % conf_path)
        file_list.append(fpath)
    formatted_list = '\n'.join(('* %s' % c for c in file_list))
    return file_list, formatted_list


def get_domains(nginx_config_files):
    """
    Return a sorted list of the set of domains in given nginx configuration
    files using `server_name` nginx directive
    """
    domains = []
    for conf_file in nginx_config_files:
        for line in open(conf_file):
            if 'server_name' not in line:
                continue
            parts = line.strip().split()
            assert len(parts) >= 2, 'Invalid `server_name` section in %s' % conf_file
            domains.extend(parts[1:])
    return sorted(set(d.strip(';') for d in domains))


def get_nginx_conf_dir():
    """ get NGINX_CONF environment variable if set, otehrwise default to '/etc/nginx/conf.d/' """
    return os.environ.get('NGINX_CONF', '/etc/nginx/conf.d/')


def get_simp_le_args(email, domains, join_args=False):
    """
    Add non empty email and domains to the default `simp_le` arguments.
    Optionally, join arguments with "\\ <linebreak>".
    """
    args = SIMP_LE_ARGS
    if email:
        args = ['--email', email] + args

    for domain in domains:
        args.extend((DOMAIN_PART_TMPL.strip() % domain.strip()).split())

    if join_args:
        args = ' \\\n'.join(args)
    return args


@click.group(invoke_without_command=True)
@click.option('--debug/--no-debug', default=False)
@click.pass_context
@click.option('-y', '--yes', is_flag=True,
              help='Confirm all prompts with default action')
@click.option('--nginx-dir', prompt=True, default=get_nginx_conf_dir,
              help='Location of nginx configuration')
@click.option('--email', prompt=True, help='Lets Encrypt account email')
def cli(ctx, debug, yes, nginx_dir, email):
    """
    This main entry point of the script is used to invoke an step-by-step
    interactive SSL setup; invoking each of the subcommands in order.
    """
    if not ctx.invoked_subcommand:
        files = ctx.invoke(get_files, nginx_dir=nginx_dir, yes=yes)
        domains = ctx.invoke(confirm_domains, debug=debug, nginx_files=files, yes=yes)
        ctx.invoke(generate_renew_script, domains=domains, yes=yes, email=email)

        # prepare and run simp_le cmd
        args = get_simp_le_args(email, domains)
        ctx.invoke(run_simp_le, debug=debug, simp_le_args=args)
        ctx.invoke(configure_ssl_nginx, yes=yes)


@cli.command('get_files')
@click.option('--nginx-dir', prompt=True, default=get_nginx_conf_dir,
              help='Location of nginx configuration')
@click.option('-y', '--yes', is_flag=True,
              help='Confirm all prompts with default action')
@click.pass_context
def get_files(ctx, nginx_dir, yes):
    """
    Find nginx configuration files, and ask user to add a challenge section
    """
    step1_a = "First, you need to modify some/all of these nginx config files:\n\n"
    step1_b = "\n\nAdd the next part to a file's `server` section:\n%s" % NGINX_CHALLENGE
    step1_c = "\n-- WARNING! you have yet to modify the following files:\n"
    step1_d = "You should now restart/reload your nginx server.\n"
    enter_prompt = "Press Enter when done..."

    all_file_list, formatted_list = get_nginx_files(nginx_dir)

    first = None
    while True:
        if not first:
            click.echo(''.join([step1_a, formatted_list, step1_b]))
            input(enter_prompt)
            first = True
            continue
        unmodified_files, formatted_list = get_nginx_files(nginx_dir, skip_modified=True)
        click.echo(''.join([step1_c, formatted_list]))
        wat = yes or input("Do you want to skip these files? [Y/quit]").lower()[:1]
        if wat in ['y', '', True]:
            break
        elif wat == 'q':
            ctx.exit('Please run me again to start over')
        else:
            continue

    click.echo(step1_d)
    input(enter_prompt)

    return list(set(all_file_list) - set(unmodified_files))


@cli.command()
@click.option('--debug/--no-debug', default=False)
@click.option('-n', '--nginx-files', multiple=True,
              help='A list of nginx configuration files')
@click.option('-d', '--domains', multiple=True, help='A list of domain names')
@click.option('-y', '--yes', is_flag=True,
              help='Confirm all prompts with default action')
@click.pass_context
def confirm_domains(ctx, debug, nginx_files, domains, yes):
    """
    Find the server_name values from the nginx config files and make sure challenge
    urls all return 404.
    """
    assert nginx_files or domains, "Either --nginx-files or --domains are required"
    if nginx_files:
        domains = list(domains) + get_domains(nginx_files)
    if debug:
        click.echo(domains)

    step2_a = "\nThese are the domains we're securing today:\n"
    click.echo(''.join([step2_a, '\n'.join(('* %s' % d for d in domains))]))

    confirmed = yes or input("Is that correct? [(y)es/(n)o/(V)erify]").lower()[:1]
    if confirmed not in ['v', 'y', True, '']:
        ctx.exit('Abort!!! Go over your config and come run again (tip: run with '
                 '`--domains` to run for specific domains')
    elif not yes:
        confirmed = confirmed == 'y'

    if not confirmed:  # verification required
        click.echo('Verifying the domains are accessible')
        responses = [requests.head('http://%s/letsencrypt/challenge/' % d, timeout=0.2)
                     for d in domains]
        if not all(r.status_code == 404 for r in responses):
            errors = ('%s returned %s' % (r.request.url, r.status_code)
                      for r in responses if not r)
            ctx.exit('Errors found:\n\n%s' % '\n'.join(errors))
        click.echo('\nGreat!')
    return domains


@cli.command()
@click.option('-d', '--domains', multiple=True, help='A list of domain names')
@click.option('-s', '--save-to', help='Directory to save `renew-certs.sh` to',
              default=os.path.join(HOME_DIR, 'renew_script.sh'), prompt=True)
@click.option('-y', '--yes', is_flag=True,
              help='Confirm all prompts with default action')
@click.option('--email', prompt=True, help='Lets Encrypt account email')
@click.pass_context
def generate_renew_script(ctx, domains, save_to, yes, email):
    """
    Using given domain names, generate a script that runs `simp_le` and stores
    the certificates in `~/letsencrypt/certs`.
    The script itself is saved by default to `~/renew_script.sh` (by default)
    and should be added e.g. as a monthly cronjob.
    """
    args = get_simp_le_args(email, domains, join_args=True)
    renew_script = SIMP_LE_TMPL % args
    if os.path.exists(save_to):
        click.echo('Renew script already exists at %s' % save_to)
        if yes:
            click.echo('Overwriting script without prompt... (--yes)')
        elif input("Do you want to overwrite? [(y)es/(N)o]").lower()[:1] != 'y':
            ctx.exit('Cowardly escape!')
    with open(save_to, 'w') as script_file:
        script_file.write(renew_script)
    click.echo("Generated renew script at %s" % save_to)
    return domains


@cli.command('simp_le', context_settings=dict(
    ignore_unknown_options=True,
    help_option_names=['--make-ssl-help']
))
@click.option('--debug/--no-debug', default=False)
@click.argument('simp_le_args', nargs=-1, type=click.UNPROCESSED)
def run_simp_le(debug, simp_le_args):
    """
    Run simp_le passing it further arguments (use `--make-ssl-help` for our help).

    Whenever run, ensures target dir (default: `CERTS_DIR`) exists
    and creates it if it is not.
    """
    if not os.path.exists(CERTS_DIR):
        os.makedirs(CERTS_DIR)

    if debug:
        simp_le_args.append('-vv')
        click.echo('Arguments are %s' % [sys.argv, simp_le_args])

    # keys are written to current dir, so change to target dir first
    os.chdir(CERTS_DIR)
    simp_le.main(cli_args=simp_le_args)


@cli.command()
@click.option('-y', '--yes', is_flag=True,
              help='Confirm all prompts with default action')
def configure_ssl_nginx(yes):
    """
    Makes sure that the generated certificates exist where we expect them, and
    display the required configuration to enable SSL in your nginx config files.
    """
    if not yes:
        keys = ['fullchain.pem', 'key.pem']
        assert all(os.path.exists(os.path.join(CERTS_DIR, k)) for k in keys), (
            "Certificate directory does not exist yet, please run `simp_le` sub-command first (or"
            " if it's your first time, follow the interactive guide in the main command).")
    click.echo("Congrats bro! Now that you have obtained the certificates, update"
               " each server configuration with the following section:")
    click.echo(NGINX_SSL)
