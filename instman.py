#!/usr/bin/env python
# Written on 2023-03-26 (Rewritten version with InstaLoader) By Alienx

import instaloader
from instaloader import FrozenNodeIterator, resumable_iteration
from datetime import datetime
from pathlib import Path
import yaml, logging, json, argparse

date_time = datetime.now().strftime("%Y/%-m/%-d :: %H:%M:%S")
users_file = Path("~/.config/instman/users.yml").expanduser()

class InstMan():
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.api = instaloader.Instaloader()
        self.load_session()
        # self.api.load_session_from_file(self.username)

    # This method is discouraged because verification issues.
    def get_session(self):
        """ Login and save session """
        self.api.context.login(self.username, self.password)
        self.api.context.save_session_to_file(self.username+".session")

    def load_session(self):
        self.api.load_session_from_file(username=self.username, filename=self.username+".session")
        logging.info("Loaded session username %s" %(self.username))

    def get_followers(self, profile):
        """ Obtain User Followers """
        logging.info("Getting followers")
        followers_list = [follower for follower in profile.get_followers()]
        return followers_list

    def get_ff(self, profile) -> None:
        """ Return Followers In Resumable_Iteration """
        i = 1
        with open("followers.txt", "a") as file:
            post_iterator = profile.get_followers()
            with resumable_iteration(
                context=self.api.context,
                iterator=post_iterator,
                load=lambda _, path: FrozenNodeIterator(**json.load(open(path))),
                save=lambda fni, path: json.dump(fni._asdict(), open(path, "w")),
                format_path=lambda magic: "followeer_{}.json".format(magic),
            ) as (is_resuming, start_index):
                for followee in post_iterator:
                    _username = followee.username
                    file.write(_username + "\n")
                    print(f"{i} ==> {_username} Added to the list")
                    i += 1
        return None

    def get_followees(self,profile):
        """ Obtain User Following """
        logging.info("Getting followings")
        following_list = [follower for follower in profile.get_followees()]
        return following_list

    def create_files(self):
        """ Check if data directory and its files exists """
        users_file.parent.mkdir(parents=True,exist_ok=True)
        users_file.touch()

    def user_file(self, userid):
        """ Create a user file that contains its full information """
        user_file = Path(f"~/.config/instman/userdata/{userid}/data.yml").expanduser()
        user_mark = Path(f"~/.config/instman/userdata/{userid}/changes.yml").expanduser()
        user_file.parent.mkdir(parents=True,exist_ok=True)
        user_file.touch()
        user_mark.touch()
        return user_file, user_mark

    def write_data_to_file(self, user_file, data):
        with open(user_file, 'w') as file:
            yaml.dump(data, file)

    def read_data(self, read_file, userid):
        """ Read and return user data """
        data = yaml.safe_load(read_file.read_text())
        if data is None:
            return None,None
        exist = userid in data
        return data,exist

    def user_data(self, users):
        """ Construct a set of data of a user and save it """
        for user in users:
            user = user.strip()
            profile = self.profile_access(user)
            logging.info(f"Checking {user} for new/previous changes.")
            p_userid = str(profile.userid)
            data = {
                f"{profile.userid}": {
                    'username': profile.username, 'full_name': profile.full_name,
                    'added_date': date_time, 'followers': profile.followers,
                    'following': profile.followees, 'is_private': profile.is_private,
                    'is_followed': profile.followed_by_viewer, 'is_following': profile.follows_viewer,
                }
            }
            users_data, exist = self.read_data(users_file, p_userid)
            if not exist:
                logging.info(f"INFO: Adding a new user {user} to users data.")
                try:
                    users_data.update(data)
                except Exception:
                    users_data = data
                self.write_data_to_file(users_file, users_data)
                self.save_data(p_userid, profile)
            self.check_change(users_data, data, p_userid, profile)

    def profile_access(self, user):
        """ Return profile based on privacy ."""
        profile = instaloader.Profile.from_username(self.api.context, user)
        return profile

    def check_change(self, old_data, new_data, userid, profile):
        """ Check for any changes in user data and log it """
        snew_data = {k: {k2: v2 for k2, v2 in v.items() if k2 != 'added_date'} for k, v in new_data.items()}
        sold_data = {k: {k2: v2 for k2, v2 in v.items() if k2 != 'added_date'} for k, v in old_data.items()}
        pot_new = []
        pot_old = []
        for key, new_values in snew_data.items():
            old_values = sold_data.get(key, {})
            if old_values != new_values:
                changed_values = {k: v for k, v in new_values.items() if old_values.get(k) != v}
                if changed_values:
                    k = next(iter(changed_values.keys()))
                    logging.info(f"Key {key} {k} was changed: {changed_values[k]} Old Value: {old_values.get(k)}")
                    pot_new.append(changed_values)
                    pot_old.append(old_values)
        if pot_new:
            item = pot_new[0]
            keys = [key for key in (iter(item.keys()))]
            self.save_changes(pot_new, pot_old, userid)
            for k in keys:
                if k in ["followers", "following"]:
                    self.detect_changes(userid, profile, k)
                    self.update_value(userid, old_data, item, k)
                else:
                    self.update_value(userid, old_data, item, k)
        else:
            logging.info("No Changes Were Detected.")

    def update_value(self,userid, old_data, change_key, k):
        """ Updates a value of a userid """
        old_data[userid][k] = change_key[k]
        self.write_data_to_file(users_file, old_data)
        logging.info(f"Successfully Written Wrote {userid} New Data.")

    def detect_changes(self, userid, profile, data_type):
        """ Detect changes that were made """
        user_file, _ = self.user_file(userid)
        user_data, _ = self.read_data(user_file, userid)
        old_data_set = set(user_data[userid][data_type])
        new_data_set = set(
            follower.username for follower in self.get_followers(profile)
        ) if data_type == "followers" else set(
            followee.username for followee in self.get_followees(profile)
        )
        diff_data = {
            "New " + data_type.capitalize(): list(new_data_set - old_data_set),
            "Lost " + data_type.capitalize(): list(old_data_set - new_data_set),
        }
        for change_type, change_data in diff_data.items():
            if change_data:
                self.data_new(userid, data_type, {change_type: change_data, "added_date": date_time})
                self.renew_data({change_type: change_data, "added_date": date_time}, userid, data_type, change_type.split()[0] + " ")

    def get_info(self, username, p=True):
        """ Get User Information and print it """
        profile = self.profile_access(username)
        metadata = {
            'username': profile.username,
            'Full name': profile.full_name,
            'User Id': profile.userid,
            'Biography': profile.biography,
            'Is Private': profile.is_private,
            'Following': profile.followees,
            'Followers': profile.followers,
            'Followes You': profile.follows_viewer,
            'You Follow': profile.followed_by_viewer,
            'Blocked You': profile.has_blocked_viewer,
            'Is Blocked': profile.blocked_by_viewer,
        }
        if p:
            print(metadata)
        return metadata

    def list_media(self, user):
        """ List media of user including all their profile stories/reels/photos """
        profile = self.profile_access(user)
        self.api.save_metadata = True
        self.api.compress_json = False
        self.api.download_geotags = True
        self.api.filename_pattern = "{profile}_{date_utc:%Y-%m-%d_%H-%M-%S}"
        # userid = []; userid.append(profile.userid)
        # a = [story for story in self.api.get_stories(userid)]
        # for story in self.api.get_stories():
        #     # story is a Story object
        #     for item in story.get_items():
        #         # item is a StoryItem object
        #         self.api.download_storyitem(item, ':stories')
        count=0
        for p in profile.get_posts():
            b = self.api.download_post(post=p, target=profile.username)
            if b and count != 1:
                count += 1
            else:
                exit(0)
        # for highlight in self.api.get_highlights(profile.userid):
        #     for item in highlight.get_items():
                # item is a StoryItem object
                # print(item.url)
                # self.api.download_storyitem(item, '{}/{}'.format(highlight.owner_username, highlight.title))

        print(a)
        # self.api.download_stories(userids=userid)
        # api.download
        return None

    def save_changes(self, changes, old_changes, userid):
        """ Save User Changes Into A File """
        _, user_mark = self.user_file(userid)
        sdata, _ = self.read_data(user_mark, userid)
        changes_keys = list(changes[0].keys())
        if not sdata:
            sdata = []
        for key in changes_keys:
            new = {
                "field": key,
                "old_value": old_changes[0][key],
                "new_value": changes[0][key],
                "date_added": date_time,
            }
            sdata.append(new)
        self.write_data_to_file(user_mark, sdata)

    def data_new(self, userid, key, new_data):
        """ Save new recorded data into a file """
        userfile = Path(f"~/.config/instman/userdata/{userid}/recorded.json").expanduser()
        userfile.touch()
        tmp, _ = self.read_data(userfile, userid)
        data = {
            userid: {
                "creation_date": date_time,
                "followers": [],
                "following": []
            }
        }
        if tmp is not None:
            tmp[userid][key].append(new_data)
            data = tmp
        if tmp is None and new_data is not None:
            data[userid][key].append(new_data)
        with open(userfile, "w") as userdata:
            json.dump(data, userdata)

    def renew_data(self, data, userid, k, v):
        """ Renew old data once changes were made """
        user_file, _ = self.user_file(userid)
        user_data, _ = self.read_data(user_file, userid)
        for item in data[v + k.capitalize()]:
            if "New" in v:
                logging.info(f"[+] Adding user {item} to db.")
                user_data[userid][k].append(item)
            else:
                logging.info(f"INFO: Removed user {item} to db.")
                user_data[userid][k].remove(item)
        self.write_data_to_file(user_file, user_data)
        logging.info(f'[+] Sucessfully Updated DB')

    def save_data(self, userid, profile):
        """ Save new data in a file """
        user_file, _ = self.user_file(userid)
        read_data, _ = self.read_data(user_file, userid)
        if not read_data:
            followers = self.get_followers(profile) # list
            followees = self.get_followees(profile) # list
            user_data = {
                userid: {
                    'followers': [follower.username for follower in followers],
                    'following': [following.username for following in followees]
                }
            }
            logging.info('[+] Created a user data file.')
            try:
                self.write_data_to_file(user_file, user_data)
                logging.info('[+] Writing followers/followings data.')
            except Exception as e:
                logging.error(f'[-] Error writing data to file: {e}')

def main():
    parser = argparse.ArgumentParser(description="InstMan An Account Monitoring Tool", add_help=True)
    parser.add_argument('-c', '--change', action="store_true", help="Mark Changes Of An Account", dest="change")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-i', '--user', type=str, nargs='+', help="Username(s) to do actions to", dest="user")
    group.add_argument('-f', '--users-file', type=argparse.FileType('r'), help="File that contains Username(s) to do actions to", dest='users')
    parser.add_argument('-u', '--username', type=str, help="Username to authenticate with", dest="auth")
    parser.add_argument('-p', '--info', action="store_true", help="Print Information of a user", dest="print")
    parser.add_argument('-m', '--media', action="store_true", help="List Username Media", dest="media")
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler('debug.log'), logging.StreamHandler()])
    Ist = InstMan(args.auth, "")
    Ist.create_files()
    if args.change:
        if args.users:
            with args.users as f:
                users = f.readlines()
                Ist.user_data(users)
        else:
            Ist.user_data(list(args.user))
    elif args.print:
        Ist.get_info(args.user[0])
    elif args.media:
        Ist.list_media(args.user[0])
    else:
        print("Nothing Checked")
main()
