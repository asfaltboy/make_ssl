# What is it

`make_ssl` is wrapper CLI tool combined with a PEX build script to make deploying and running `simp_le` even simpler!

<!-- MarkdownTOC autolink=true bracket=round -->

- [Usage](#usage)
  - [Why do I need it](#why-do-i-need-it)
- [How does it work](#how-does-it-work)
  - [What's `simp_le`](#whats-simp_le)
  - [PEX build script](#pex-build-script)
  - [CLI tool](#cli-tool)
- [Building](#building)

<!-- /MarkdownTOC -->


## Usage

    Usage: make-ssl-osx [OPTIONS] COMMAND [ARGS]...

      This main entry point of the script is used to invoke an step-by-step
      interactive SSL setup; invoking each of the subcommands in order.

    Options:
      --debug / --no-debug
      -y, --yes             Confirm all prompts with default action
      --nginx-dir TEXT      Location of nginx configuration
      --email TEXT          Lets Encrypt account email
      --help                Show this message and exit.

    Commands:
      configure_ssl_nginx    Makes sure that the generated certificates...
      confirm_domains        Find the server_name values from the nginx...
      generate_renew_script  Using given domain names, generate a script...
      get_files              Find nginx configuration files, and ask user...
      simp_le                Run simp_le passing it further arguments (use...

## Why do I need it

If you're like me, you love and use [Let's Encrypt][1] often. This tool aims to assist in
performing the (repetitive) actions required to secure each domain you work on.

Read more about Let's Encrypt at their [official site][4].

# How does it work

## What's `simp_le`

[`simp_le`][2], a simple Let's Encrypt client, is an excellent tool written by [Jakub Warmuz][3] who works on the [official Let's Encrypt client][5].

For a short tutorial on Let's Encrypt using `simp_le` check out [this blog entry][6]. 

## PEX build script

The `build.sh` bash script generates a [PEX (Python EXecutable)][8] file, a stand-alone packaged executable for the CLI tool and it's dependencies (`click`, `simp_le`, and all the required cryptography libs). I found this to be a really nice way to freeze all requirements while avoiding the need to re-build dependencies (for non-wheel packages) for every machine we want to secure.

If you want to understand how PEX works, I encourage you to [watch this video introduction][7] by [Brian Wickman][9].

## CLI tool

This is simple CLI wrapper for running `simp_le`, and aims to provide a step-by-step guide (using prompts) to getting certs and securing your Nginx http server. When called without positional arguments, it currently follows the following steps:

1. Prompt for the location of nginx config files directory and read every nginx FILE.conf found in above dir, and if it does not contain `acme-challenge`, save the domains listed. Also prints out the required nginx config changes to add the challenge.
2. For every domain, verify it is reachable on http://domain (using requests).
3. Generates a certificate renewal script, to be run as a monthly cronjob.
4. Run `simp_le` with built arguments to initially generate LE account and certs.
5. Print out the required nginx config changes to configure ssl server with generated certificates (some assumptions are made in regards with protocols, strictness and ciphers).

Each of the above is also callable as an independent sub-command, e.g. running `make-ssl-osx generate_renew_script` will generate the "renew certificates" script. While each sub-command should prompt for required arguments (or use sane defaults), these can also be provided with options; see `--help` on any sub-command for more info.

To achieve the slick command line interface, [Armin Ronacher][11]'s [`click`][10] is used.

# Building

To build locally (for your machine's architecture) simply run the bash build script:

    $ ./build.sh <platform>

    # for example to build for OSX
    $ ./build.sh osx

This will create the PEX files at `build/make-ssl-<platform>`.

If you are on OSX and would like to build for Linux, a CentOS based Dockerfile is available to automate that process:

    $ docker build -t make_ssl .
    $ docker run -v `pwd`/build:/src/pex_make_ssl/build -it make_ssl 


[1]: https://letsencrypt.org/
[2]: https://github.com/kuba/simp_le
[3]: https://github.com/kuba
[4]: https://letsencrypt.org/about/
[5]: https://github.com/letsencrypt/letsencrypt
[6]: https://blog.nytsoi.net/2016/01/08/automating-letsencrypt-with-simp_le
[7]: https://www.youtube.com/watch?v=NmpnGhRwsu0
[8]: https://pex.readthedocs.org/en/stable/
[9]: https://github.com/wickman
[10]: http://click.pocoo.org/5/
[11]: http://lucumr.pocoo.org/about/
