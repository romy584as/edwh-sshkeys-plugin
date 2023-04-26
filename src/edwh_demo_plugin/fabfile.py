from fabric import task
from datetime import datetime
from tabulate import tabulate
from yaml.loader import SafeLoader
from termcolor import colored
import pathlib
import yaml
import pprint
import time
import os

YAML_KEYS_PATH = pathlib.Path("~/.ssh/known_keys.yaml")

# met irerable kan je meerdere cli keys in 1 regel meegeven.
@task(iterable=['command_line_key'])
# append key to remote is kort gezegd dat je via de YAML file de public key IN de opgegeven remote machine zet
def add_remote_old(c, command_line_key):
    '''
    command-line-key is/zijn de key(s) die je toevoegd aan de remote machine.
    Je kan meerdere opgeven.

    Als er een key bij zit die NIET in de yaml file staat kan je die aanmaken door bij de input vraag 'y' mee te geven.
    LET OP: je moet dan wel een bericht mee geven, anders breekt het programma af.

    De private/public key staan in de ~/.managed_ssh_keys-{key_name}
    '''
    # open de yaml file zodat die kan lezen welke head_keys er al zijn
    with open('key_holder.yaml', 'r') as yaml_file:
        key_db: dict = yaml.load(yaml_file, Loader=SafeLoader)
        all_key_information = key_db.setdefault('keys')
        count_keys = 0
        # controleert of het aantal command_line_key's wel gelijk staan aan de keys die nodig zijn, zo niet gaat die je vragen in de cli of de onjuiste key wil veranderen
        for head_keys in all_key_information:
            if head_keys in command_line_key:
                count_keys += 1
        if count_keys == len(command_line_key):
            for which_key in command_line_key:
                for head_keys in all_key_information:
                    if which_key in head_keys:
                        for key, value in all_key_information[head_keys].items():
                            # gaat alleen de 'sleutel' toevoegen en niet de datetime enzovoort
                            if bool(key.find('datetime')) and bool(key.find('who@hostname')) and bool(
                                    key.find('message')) is True:
                                c.run(f'echo {value} >> ~/.ssh/authorized_keys')
                                c.run('touch ~/.ssh/keys')
                                c.run('sort -u ~/.ssh/authorized_keys > ~/.ssh/keys')
                                time.sleep(1)
                                c.run('cp ~/.ssh/keys ~/.ssh/authorized_keys')
                                c.run('rm ~/.ssh/keys')
                                print(f'Het is gelukt! De \033[1m{which_key}\033[0m key is toegevoegd.')
        else:
            # verwijder alle keys die WEL in de yaml file staan
            not_in_yaml_keys = command_line_key
            for head_keys in all_key_information:
                not_in_yaml_keys = [which_key for which_key in not_in_yaml_keys if which_key not in head_keys]
            print(
                f'Verkeerde \033[1m{" ".join(not_in_yaml_keys)}\033[0m key, controleer eerst of je de juiste key hebt ingevuld. Of als die wel in de YAML file staat.')
            for which_key in not_in_yaml_keys:
                split_key = which_key.replace('-', ' ')
                generate_doel = ''
                if len(split_key.split()) == 3:
                    generate_doel = split_key.split()[2]
                # maak de key aan die nog NIET in de yaml file stond
                if input(f"Wil je de {which_key} key aanmaken? [Y/n]: ") in ("y", "Y", ""):
                    generate_message = str(input('Wat is het bericht dat je mee wilt geven? Deze MOET: '))
                    if generate_message == '':
                        print('Je moet een message invullen!')
                        exit(1)
                    # print('\n\nJe moet minimaal 2/3 invullen: Owner, Hostname en/of Doel!!\n\n')
                    # owner = str(input("Wie is de owner van de Private key?"'\n')) or ''
                    # hostname = str(input('Wie is de specifieke host? bvb: productie - testomgeving - naam van de stagiar''\n')) or ''
                    # doel = str(input('Waarom maak je deze key aan?''\n')) or ''
                    # generate(c, message, owner=owner.replace(" ", ""), hostname=hostname.replace(" ", ""), doel=doel.replace(" ", ""))
                    # voer dus de functie generate uit om de key dus daadwerkelijk aan te maken
                    generate_old(c, generate_message, owner=split_key.split()[0], hostname=split_key.split()[1],
                                 doel=generate_doel)
                    # bekijk of nu wel alle keys in de yaml file staan, zo ja, ga dan alsnog toevoegen
                    if head_keys in command_line_key:
                        count_keys += 1
                    if count_keys == len(command_line_key):
                        add_remote_old(c, command_line_key)

def create_known_keys_yaml_if_not_exists(c):
    if not pathlib.Path.is_file(pathlib.Path(YAML_KEYS_PATH)):
        setup_known_keys()
        print(colored("You have no keys, please run the 'generate' command first.", "red"))
        # ask the user if he/she want to generate a key
        if input("Would you like to generate a key? [Y/n]: ").replace(" ", "") in ("y", "Y", ""):
            generate(c)
        else:
            print(":/")
            exit(1)


@task(iterable=['command_line_key'])
def add_remote(c, command_line_key):
    """
    It adds the specified SSH key(s) to the remote machine.
    :param c: run commands.
    :param command_line_key: List of keys to be added
    :return: None
    """
    create_known_keys_yaml_if_not_exists(c)
    yaml_file = open(YAML_KEYS_PATH)
    # create dictionary form yaml file
    yaml_keys: dict = yaml.load(yaml_file, Loader=SafeLoader)
    # sets key 'keys' to None if no value is set
    all_key_information = yaml_keys.setdefault('keys')
    keys = [head_keys for head_keys in all_key_information if head_keys in command_line_key]
    key_count = len(keys)


# met irerable kan je meerdere cli keys in 1 regel meegeven
@task(iterable=['command_line_key'])
# delete key from remote is kort gezegd dat je via de YAML file de public key UIT de opgegeven remote machine zet
def delete_remote(c, command_line_key):
    """
    Removes the specified SSH key(s) from the remote machine.
    :param c: Connection object
    :param command_line_key: List of keys to be removed
    """
    with open('key_holder.yaml', 'r') as yaml_file:
        key_db = yaml.safe_load(yaml_file)
        all_key_information = key_db.get('keys', {})

    for which_key in command_line_key:
        for head_keys in all_key_information:
            if which_key in head_keys:
                for key, value in all_key_information[head_keys].items():
                    if key not in ['datetime', 'who@hostname', 'message']:
                        c.run(f'grep -v "{value}" ~/.ssh/authorized_keys > ~/.ssh/keys')
                        c.run('mv ~/.ssh/keys ~/.ssh/authorized_keys')
                        print(f'Success! The {which_key} key has been removed.')


def setup_known_keys():
    """
    creates a yaml file at ~/.ssh/known_keys.yaml for key configurations0

    :return: None
    """
    if not pathlib.Path.is_file(pathlib.Path("~/.ssh/known_keys.yaml")):
        known_keys_yaml = open(pathlib.Path("~/.ssh/known_keys.yaml"), "x")
        known_keys_yaml.close()

@task
def generate():
    ...

@task
def generate_old(c, message, owner='', hostname='', doel=''):
    '''
    message: Geef een verduidelijke bericht mee aan de key die gegenareerd wordt.
    owner: Wie heeft de private key..?
    hostname: Specifieke host, bvb: productie - testomgeving - naam van de stagiar
    doel: Waarom maak je deze key aan? bvb: Sandfly, SSH
    De private/public key staan in de ~/.managed_ssh_keys-{key_name}
    '''
    # bekijk of de key_holder.yaml al bestaat, zo nee, maak die dan aan. zo ja, zorg er dan voor dat de keys
    # standaard wordt
    try:
        with open('key_holder.yaml', 'r') as stream:
            key_db: dict = yaml.load(stream, Loader=SafeLoader)
            all_key_information = key_db.setdefault('keys')
    except FileNotFoundError:
        os.popen('touch key_holder.yaml | echo "keys" > key_holder.yaml')
        all_key_information = {}
    # hierbij wordt gekeken of er wel 2/3 argumenten zijn, zo ja wordt het dan ook meteen op de goeie volgorde gezet
    how_many_arguments_in_cli = bool(owner != ''), bool(hostname != ''), bool(doel != '')
    if sum(how_many_arguments_in_cli) < 2:
        print("Je moet minimaal twee van de drie argumenten meegeven: Owner, Hostname, Doel")
        exit(1)
    key_name = []
    if bool(owner):
        key_name.append(owner)
    if bool(hostname):
        key_name.append(hostname)
    if bool(doel):
        key_name.append(doel)
    key_name = '-'.join(key_name)
    if key_name in all_key_information:
        print(f'{key_name} bestaat al, toevoegen afgebroken.')
        exit(1)
    print('De key wordt aangemaakt...')
    # met ssh-keygen wordt de key pair dus aangemaakt en wordt de public key in de yaml file gezet
    os.popen(f'ssh-keygen -t rsa -b 4096 -f ~/.managed_ssh_keys-{key_name} -N "" -C "{message}"').close()
    whoami_local_handle = os.popen('echo "$(whoami)@$(hostname)"')
    time.sleep(4)
    whoami_local = whoami_local_handle.read().replace('\n', '')
    whoami_local_handle.close()
    cat_local_public_key_handle = os.popen(f'cat ~/.managed_ssh_keys-{key_name}.pub')
    cat_local_public_key = cat_local_public_key_handle.read().replace('\n', '')
    cat_local_public_key_handle.close()
    # zo komt het dus er uit te zien in de yaml file
    sleutel_dict = {
        'keys':
            {key_name:
                {
                    'sleutel': cat_local_public_key,
                    'datetime': datetime.today().strftime("Datum: %Y-%m-%d Tijdstip: %H:%M:%S"),
                    'who@hostname': whoami_local,
                    'message': message
                }
            }
    }
    # voor de eerste keer (wanneer het script dus nog niet bestond) wordt de hoofdkey keys nog aangemaakt en anders wordt het erin toegevoegd.
    with open('key_holder.yaml', 'w') as stream:
        try:
            if key_db is not None:
                new_key_dict = sleutel_dict.pop('keys')
                all_key_information.update(new_key_dict)
                yaml.dump(key_db, stream, indent=4)
                pprint.pprint(new_key_dict)
                print(f'De private/public key staan in de ~/.managed_ssh_keys-{key_name}')
        except:
            yaml.dump(sleutel_dict, stream, indent=4)
            pprint.pprint(sleutel_dict)
            print(f'De private/public key staan in de ~/.managed_ssh_keys-{key_name}')


@task
def list_old(c):
    """
    Je krijgt een overzicht te zien van alle keys
    Als er ook al keys remote staan dan worden er twee lijstjes gemaakt: local & remote :::: remote
    Als er nog keys staan in de remote file en die niet herkent worden, krijg je de output te zien van die keys
    """
    with open('key_holder.yaml', 'r') as yaml_file:
        key_db: dict = yaml.load(yaml_file, Loader=SafeLoader)
        all_key_information = key_db.setdefault('keys')
    cat_remote_keys = c.run('cat ~/.ssh/authorized_keys', hide=True)
    cat_remote_keys = cat_remote_keys.stdout
    rows = []
    row_x = []
    row_y = []
    cat_list = []
    split_the_cat_list = '\|'
    clolumn_names = ['\033[1mlocal & remote', 'local\033[0m']
    for head_keys in all_key_information:
        # all_key_information[head_keys].items() laat de keys en values zien die in de sleutel staan
        for key, value in all_key_information[head_keys].items():
            # verwijder de datetime, who@hostname en message. zodat je alleen de sleutel te zien krijgt.
            if bool(key.find('datetime')) and bool(key.find('who@hostname')) and bool(key.find('message')) is True:
                # als de key value in de cat (remote keys file) staan:
                if value in cat_remote_keys:
                    # voeg dan die sleutel toe aan de row_x
                    row_x.append(head_keys)
                    cat_list.append(value)
                # als de key value NIET in de cat staat:
                else:
                    # voeg dan de sleutel toe aan de row_y
                    row_y.append(head_keys)
    try:
        # kijk of er nog andere keys op de remote machine staan, zo ja, geef daar dan de output van
        grep_cat_list = c.run(f'grep -v "{split_the_cat_list.join(cat_list)}" ~/.ssh/authorized_keys', hide=True)
        print('LET OP!')
        print('Er staan nog andere keys op de remote, alleen kan die niet herkend worden door het yaml file:\n')
        print(grep_cat_list.stdout)
        print()
    except:
        pass
    # dit zorgt ervoor dat de keys in de goede column komt te staan
    for bron_index in range(max(len(row_x), len(row_y))):
        rows.append([])
    for bron_index in range(max(len(row_x), len(row_y))):
        if bron_index < len(row_x):
            rows[bron_index].append(row_x[bron_index])
        if bron_index < len(row_y):
            rows[bron_index].append(row_y[bron_index])
        if len(rows[bron_index]) == 1:
            if not bool(''.join(rows[bron_index]) in row_x):
                rows[bron_index].insert(0, '')
                print(rows[bron_index][0])
    print('\033[1mDe lijst van de keys:\033[0m')
    if bool(row_x):
        print(tabulate(rows, headers=clolumn_names))
    else:
        print('Er staan nog geen keys op deze remote machine die in de yaml file staan...')
        print('\033[1mlocal\033[0m')
        for head_keys in all_key_information:
            print(head_keys)

