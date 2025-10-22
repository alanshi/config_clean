
mkdir vendor

pip download --platform linux_x86_64 --python-version 3.12 --abi cp312 --only-binary=:all: --no-deps  -r requirements.txt -d vendor