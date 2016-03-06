#!/bin/bash
if [ $PYPI_INDEX ]; then SET_INDEX="-i $PYPI_INDEX"; fi
if [ $@ ]; then TARGET=$@; else TARGET="linux"; fi
BUILD_TARGET_NAME="make-ssl-$TARGET" 
echo $BUILD_TARGET_NAME
if [ $TARGET = "osx" ]; then
	BUILD_PLATFORM="macosx-10.11-x86_64"
else

	BUILD_PLATFORM="linux-x86_64"
fi

echo "building $BUILD_TARGET_NAME"
rm -rf .deps
rm -rf make_ssl.egg-info/
rm -rf ~/.pex/build/make_ssl*.whl
rm -rf $BUILD_TARGET_NAME
pex -r make-ssl-req.txt -o build/$BUILD_TARGET_NAME $SET_INDEX . -e make_ssl:cli -v --platform $BUILD_PLATFORM
