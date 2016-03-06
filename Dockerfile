FROM centos:centos7
MAINTAINER Pavel Savshenko <pavel@izzysoftware.com>

RUN yum -y install epel-release vim
RUN yum makecache fast

RUN yum -y install gcc python-devel libffi-devel openssl-devel

WORKDIR /src/
ADD https://bootstrap.pypa.io/get-pip.py .
RUN python get-pip.py
RUN pip install requests pex

ADD . /src/pex_make_ssl/
WORKDIR /src/pex_make_ssl/
ENTRYPOINT ["/bin/bash", "build.sh"]
