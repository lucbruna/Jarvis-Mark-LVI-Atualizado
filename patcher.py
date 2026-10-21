import os, sys, json, subprocess, tempfile, shutil

def patch():
    install_dir = os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'Torvis')
    edition = os.path.join(install_dir, 'edition.json')
    if not os.path.exists(edition):
        print('edition.json not found')
        return 1
    # backup
    shutil.copyfile(edition, edition + '.bak')
    with open(edition, 'r', encoding='utf-8') as f:
        data = json.load(f)
    data.setdefault('relay', {})['url'] = ''
    data['relay']['cert'] = ''
    if 'update_key' in data:
        data['update_key'] = ''
    with open(edition, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)
    print('patched')
    return 0

def main():
    # if installer present alongside, run it first
    here = os.path.dirname(os.path.abspath(sys.argv[0]))
    installer = os.path.join(here, 'Torvis-setup.exe')
    if os.path.exists(installer):
        subprocess.run([installer, '/VERYSILENT', '/SUPPRESSMSGBOXES'], check=False)
    rc = patch()
    sys.exit(rc)

if __name__ == '__main__':
    main()
