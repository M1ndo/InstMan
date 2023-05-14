#!/usr/bin/env python
# Written on 2023-03-26 (Rewritten version with InstaLoader) By Alienx

from library.instaloader.instaloader import instaloader
# import instaloader
# from instaloader import FrozenNodeIterator, resumable_iteration
# from instaloader import Highlight, Story, Profile, Post, PostComment
from library.instaloader.instaloader.structures import PostLocation, Highlight, Story, Post, Hashtag, Profile, PostComment
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
from typing import Tuple, Union, List, Dict, Any
from multiprocessing.pool import ThreadPool
from args_format import arguments
from postdata import GetInfo
import yaml, logging, json, time
from pdb import set_trace as bp


date_time = datetime.now().strftime("%Y/%-m/%-d :: %H:%M:%S")
users_file = Path("~/.config/instman/users.yml").expanduser()
debug_path = Path("~/.config/instman/debug.log").expanduser().as_posix()

class InstMan():
    def __init__(self, username, password, debug=True):
        self.username = username
        self.password = password
        self.api = instaloader.Instaloader(quiet=debug) # type: ignore
        self.profile = None
        self.load_session()
        # self.api.load_session_from_file(self.username)

    # This method is discouraged because verification issues.
    def get_session(self):
        """ Login and save session """
        self.api.context.login(self.username, self.password)
        self.api.context.save_session_to_file(self.username+".session")

    def load_session(self):
        self.api.load_session_from_file(username=self.username, filename=Path(f"~/.config/instman/{self.username}.session").expanduser().as_posix())
        logging.info("Loaded session username %s" %(self.username))

    def get_followers(self, profile: Profile) -> List[Profile]:
        """ Obtain User Followers """
        logging.info(f"[+] Getting {profile.username} followers")
        followers_list = [follower for follower in profile.get_followers()]
        return followers_list

    def get_hashtags(self, profile: Profile) -> List[Hashtag]:
        hashtags = [hash for hash in profile.get_followed_hashtags()]
        return hashtags

    def get_userinfo(self, profile: Profile) -> Any:
        """ Get Account Creation Date """
        getdata = GetInfo(profile.username, profile.userid)
        params = {
            'appid': 'com.instagram.interactions.about_this_account',
            'params': '{"target_user_id":"AAAAAAAAAAAA","referer_type":"ProfileUsername"}',
            'type': 'app',
            '__d': 'www',
            '__bkv': '7c084f1cc1fe7eaaaaa97971b0de301d974fa2672f0129dc0f7af1eeec8a'
        }
        url = "https://www.instagram.com/async/wbloks/fetch/"
        session = self.api.context._session
        data = getdata.create_date(session, url, params)
        # ret_data = self.api.context.get_json(path="async/wbloks/fetch/", params=params, post=True)
        print(data.text)

    # def get_ff(self, profile) -> None:
    #     """ Return Followers In Resumable_Iteration """
    #     i = 1
    #     with open("followers.txt", "a") as file:
    #         post_iterator = profile.get_followers()
    #         with resumable_iteration(
    #             context=self.api.context,
    #             iterator=post_iterator,
    #             load=lambda _, path: FrozenNodeIterator(**json.load(open(path))),
    #             save=lambda fni, path: json.dump(fni._asdict(), open(path, "w")),
    #             format_path=lambda magic: "followeer_{}.json".format(magic),
    #         ) as (is_resuming, start_index):
    #             for followee in post_iterator:
    #                 _username = followee.username
    #                 file.write(_username + "\n")
    #                 print(f"{i} ==> {_username} Added to the list")
    #                 i += 1
    #     return None

    def get_followees(self, profile: Profile) -> List[Profile]:
        """ Obtain User Following """
        logging.info(f"[+] Getting {profile.username} followings")
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
        user_post = Path(f"~/.config/instman/userdata/{userid}/postdata.json").expanduser()
        user_file.parent.mkdir(parents=True,exist_ok=True)
        user_file.touch()
        user_mark.touch()
        user_post.touch()
        return user_file, user_mark, user_post

    def write_data_to_file(self, user_file, data):
        with open(user_file, 'w') as file:
            yaml.dump(data, file)

    def read_data(self, read_file: Path, userid: str) -> Tuple:
        """ Read and return user data """
        data = yaml.safe_load(read_file.read_text())
        if data is None:
            return None,None
        exist = userid in data
        return data,exist

    def read_write(self, file, data, mode='r'):
        """ read And write data in json format """
        with open(file, mode) as fdata:
            if mode=='r':
                try:
                    return json.load(fdata)
                except:
                    return None
            json.dump(data, fdata)

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
        profile = instaloader.Profile.from_username(self.api.context, user) # type: ignore
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
        user_file, _, _ = self.user_file(userid)
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

    def get_info(self, username: str, p=True) -> dict:
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

    def get_stories_or_highlights(self, userid: list, download=False, stories=True, highlights=False) -> List[Union[Story, Highlight]]:
        """ Retrieves/Downloads Stories or Highlights of giving user doesn't not mark as seen """
        media_list = []
        if stories:
            media_list += [story for story in self.api.get_stories(str(userid[0]))]
        if highlights:
            media_list += [high for high in self.api.get_highlights(userid[0])]
        if download:
            for media in media_list:
                media_type = "Highlight" if isinstance(media, Highlight) else "Story"
                media_title = "Highlight " + media.title if media_type == 'Highlight' else ''
                logging.info(f"Downloading {media_title} total items [{media.itemcount}].")
                with tqdm(total=media.itemcount, desc=f"Downloading {media_type} {media_title}", colour="#6a5acd", unit_scale=True, unit="MB", smoothing=0.5) as pbar:
                    for item in media.get_items():
                        path = f"media/{media.owner_username}/stories/" if media_type == "Story" else f"media/{media.owner_username}/highlights/{media.title}/"
                        if self.api.download_storyitem(item=item, target=Path(path)):
                            pbar.update(1)
        return media_list

    def get_posts(self, profile: Profile, comments:bool=False, download:bool=False) -> Tuple[List[Post], List[Dict[str, Union[str, List[PostComment]]]]]:
        """ Retrieve/Download User posts """
        posts = [post for post in profile.get_posts()]
        lcomments = []
        if download:
            logging.info(f"Downloading {profile.username} Posts.")
            pool = ThreadPool()
            results = pool.map_async(self.download_post, posts)
            pool.close()
            with tqdm(total=len(posts), desc="Downloading Posts", unit="post") as pbar:
                while not results.ready():
                    pbar.update(len(posts) - pbar.n)
                    time.sleep(0.1)
            pool.join()
        if comments:
            lcomments = [{'postcode': post.shortcode, 'postcomment': list(post.get_comments())} for post in posts]
        return posts, lcomments

    def download_post(self, post):
        post_dir = post.date_local.strftime("%Y-%m-%d_%H%M%S")
        path = f"media/{post.owner.username}/posts/{post_dir}/"
        if self.api.download_post(post=post, target=Path(path)):
            return post, True
        else:
            return post, False

    def get_location(self, location: Union[PostLocation, None]) -> dict:
        """ Return a location TypeDict """
        return {
            "name": location.name if location else None,
            "lat": location.lat if location else None,
            "lng": location.lng if location else None,
        }

    def list_media(self, user, highlights:bool=False, stories:bool=False, posts:bool=False, comments:bool=False, download:bool=False):
        """ List media of user including all their profile stories/reels/photos """
        profile = self.profile_access(user)
        self.profile = profile
        self.api.save_metadata = True
        self.api.compress_json = False
        self.api.post_metadata_txt_pattern = ''
        self.api.download_comments = True
        # self.api.download_geotags = True
        self.api.context.quiet = True
        if comments and not posts: posts=True
        userid = [profile.userid]
        highlights_and_stories = self.get_stories_or_highlights(userid,highlights=highlights, stories=stories, download=download)
        if posts:
            r_posts, r_comments = self.get_posts(profile, comments=False, download=download)
            data = self.handle_posts(r_posts, r_comments)
            self.mark_changes(data=data, type="posts", userid=str(userid[0]))
        if highlights_and_stories:
            for media in highlights_and_stories:
                if isinstance(media, Story):
                    print(media.latest_media_local)
                    for item in highlights_and_stories[0].get_items():
                        print(dir(item))
        return None

    def handle_posts(self, posts: List[Post], comments: List[Dict[str, Union[str, List[PostComment]]]]) -> dict:
        """ Handler for processing posts """
        data = {}
        if posts:
            comments_by_postcode = {}
            for comment in comments:
                postcode = comment.get('postcode')
                if postcode:
                    comments_by_postcode.setdefault(postcode, []).append(comment)
            for post in posts:
                post_comments = comments_by_postcode.get(post.shortcode, [])
                likers = [like for like in post.get_likes()]
                post_data = {
                    "postdate": post.date_utc.strftime("%Y-%m-%d_%H%M%S"),
                    "caption": post.caption,
                    "caption_mentioned": post.caption_mentions,
                    "caption_hashtags": post.caption_hashtags,
                    "tagged": post.tagged_users,
                    "media_count": post.mediacount,
                    "total_likes": post.likes,
                    "total_comments": post.comments,
                    "liked_by": [user.username for user in likers],
                    "location": self.get_location(post.location),
                    "video_view_count": post.video_view_count,
                    "comments": {}
                }
                data[post.shortcode] = post_data
                for com in post_comments:
                    for comment in com['postcomment']:
                        data[post.shortcode]['comments'][comment.id] = {comment.owner.username: comment.text}
        return data

    def media_changed(self, new_data: dict, old_data: dict, userid: str, type: str="posts"):
        """ Track user media change from posts/stories/highlights """
        if len(new_data) != len(old_data):
            logging.info(f"Media {type} has been changed from {len(old_data)} to {len(new_data)}")
            deleted = set(old_data.keys()).difference(new_data.keys())
            new = set(new_data.keys()).difference(old_data.keys())
            changed = [{type: len(new_data)}]
            old_changed = [{type: len(old_data)}]
            self.save_changes(changed, old_changed, userid)
            return new, deleted
        else:
            logging.info(f"No {type} changes were found")
            return False

    def check_downloaded(self, date: str) -> bool:
        """ Check if media is downloaded """
        dir = Path(Path.cwd().parent.as_posix()+f"/media/{str(self.profile.username)}/{date}/") # type: ignore
        if dir.is_dir():
            return True
        return False

    def mark_changes(self, data: dict, type: str, userid: str) -> None:
        """ Mark/Save Changes from stories/highlights/posts """
        _, _, post_file = self.user_file(userid)
        post_data = self.read_write(post_file, data=None) or {}
        if not post_data:
            logging.info(f"No {type} metadata was saved yet, saving..")
            post_data.update(data)
            self.read_write(post_file, post_data, mode='w')
            return
        try:
            new, deleted = self.media_changed(data, post_data, userid, type=type)  # type: ignore
            if new:
                post_data.update(data)
                logging.info(f"{type} item {data['caption']} has been added to db")
            if deleted:
                deleted_post = post_data.pop(list(deleted)[0])
                if self.check_downloaded(deleted_post['postdate']):
                    logging.info(f"Luckily deleted {type} {deleted_post['caption']} was already downloaded")
                else:
                    logging.info(f"Unlucky deleted {type} {deleted_post['caption']} was not downloaded before")
                    logging.info("But its metadata is still saved for data processing")
                self.media_new({list(deleted)[0]: deleted_post}, userid)
            self.read_write(post_file, post_data, mode='w')
        except Exception as e:
            logging.info(f"{type} items are already at their latest")
            return

    def save_changes(self, changes, old_changes, userid):
        """ Save User Changes Into A File """
        _, user_mark, _ = self.user_file(userid)
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
        self.read_write(userfile, data, mode='w')

    def media_new(self, data, userid):
        """ Save deleted metadata """
        dfile = Path(f"~/.config/instman/userdata/{userid}/deleted_media.json").expanduser()
        dfile.touch()
        old_data, _ = self.read_data(dfile, userid)
        if not old_data:
            old_data = {}
        old_data.update(data)
        self.read_write(dfile, old_data, mode='w')

    def renew_data(self, data, userid, k, v):
        """ Renew old data once changes were made """
        user_file, _, _ = self.user_file(userid)
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
        user_file, _, _ = self.user_file(userid)
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
    parser = arguments()
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        handlers=[logging.FileHandler(debug_path), logging.StreamHandler()])
    Ist = InstMan(args.auth, "", debug=args.debug)
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
        Ist.list_media(args.user[0], args.highlights, args.stories, args.posts, args.download)
    else:
        # profile = Ist.profile_access(args.user[0])
        # print(Ist.get_hashtags(profile))
        # Ist.get_userinfo(profile)
        print("Nothing Checked")
main()
