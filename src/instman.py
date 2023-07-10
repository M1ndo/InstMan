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
from typing import Tuple, Union, List, Dict, Any, Set
from multiprocessing.pool import ThreadPool
from collections import defaultdict
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
        logging.info("Testing %s session validation." %(self.username))
        if not self.api.test_login():
            logging.info("Error session has been expired")
            logging.info("Generate a new session")
            exit(1)

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

    def user_file(self, userid: str, file_type: str) -> Path:
        """Create a user file that contains its full information"""
        file_type_map = {
            "data": "data.yml",
            "changes": "changes.yml",
            "postdata": "postdata.json",
            "storydata": "storydata.json"
        }
        user_data_dir = Path("~/.config/instman/userdata").expanduser()
        file_path = user_data_dir / userid / file_type_map.get(file_type) # type: ignore
        if file_path:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()
            return file_path
        # Add an assertion to guarantee a Path object is returned
        assert False, "Invalid file type"

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

    def user_data(self, users, ignored=False):
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
            if ignored:
                self.detect_changes(p_userid, profile, data_type=["followers", "following"])
            else: self.check_change(users_data, data, p_userid, profile)

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

    def detect_changes(self, userid: str, profile: Profile, data_type: Union[List, str]):
        """ Detect changes that were made """
        if isinstance(data_type, list):
            for item in data_type:
                self.detect_changes(userid, profile, item)
            return
        user_file = self.user_file(userid, "data")
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
        has_changes = any(change_data for _, change_data in diff_data.items())
        for change_type, change_data in diff_data.items():
            if change_data:
                self.data_new(userid, data_type, {change_type: change_data, "added_date": date_time})
                self.renew_data({change_type: change_data, "added_date": date_time}, userid, data_type, change_type.split()[0] + " ")
        if not has_changes:
            logging.info(f"[-] User {profile.username} has no hidden changes in {data_type}")

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
                        path = f"media/{media.owner_username}/stories/story_{item.date_local.strftime('%Y-%m-%d')}/" if media_type == "Story" else f"media/{media.owner_username}/highlights/{media.unique_id}_{media.title}/"
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
            r_posts, r_comments = self.get_posts(profile, comments=comments, download=download)
            data = self.handle_posts(r_posts, r_comments)
            self.mark_changes(data=data, type="posts", userid=str(userid[0]))
        if highlights_and_stories:
            data = self.handle_otherm(highlights_and_stories)
            if data['highlights']:
                self.mark_changes(data=data, type="highlights", userid=str(userid[0]))
            elif data['stories']:
                self.mark_changes(data=data, type="stories", userid=str(userid[0]))
            else:
                logging.info("[!] No stories nor highlights were found.")

    def handle_otherm(self, items: List[Union[Story, Highlight]]) -> Dict[str, Dict[str, Union[str, Dict[str, str], bool]]]: # FIXME Only handling 1 dict.
        """Handler for processing stories and highlights"""
        data = {"highlights": {}, "stories": {}}
        for media in items:
            for item in media.get_items():
                shared_to_fb = item._node.get('iphone_struct', {}).get('has_shared_to_fb') == 3
                fb_user_tags = item._node.get('iphone_struct', {}).get('fb_user_tags', {})
                media_origndate = item._node.get('iphone_struct', {}).get('imported_taken_at')
                original_date = datetime.fromtimestamp(media_origndate).strftime("%Y-%m-%d_%H:%M:%S") if media_origndate else None
                clickable_items = item._node.get('tappable_objects')
                shared_from_fb = item._node.get('iphone_struct', {}).get('is_fb_post_from_fb_story')
                post_data = {
                    item.shortcode: {
                        "upload_date": item.date_local.strftime("%Y-%m-%d_%H:%M:%S"),
                        "expire_seen": item.expiring_local.strftime("%Y-%m-%d_%H:%M:%S"),
                        "original_date": original_date,
                        "mentions": {},
                        "clickable_items": clickable_items,
                        "fb_user_tags": fb_user_tags,
                        "shared_from_fb": shared_from_fb,
                        "shared_to_fb": shared_to_fb
                    }
                }
                if isinstance(media, Highlight):
                    data["highlights"].setdefault(media.title, {}).update(post_data) # replace unique_id
                elif isinstance(media, Story):
                    data["stories"].update(post_data)
        return data

    def handle_posts(self, posts: List[Post], comments: List[Dict[str, Union[str, List[PostComment]]]]) -> Dict[str, dict]:
        """ Handler for processing posts """
        data = {"posts": {}}
        comments_by_postcode = defaultdict(list)
        for comment in comments:
            postcode = comment.get('postcode')
            if postcode:
                comments_by_postcode[postcode].append(comment)

        for post in posts:
            post_comments = comments_by_postcode.get(post.shortcode) or []
            likers = [like.username for like in post.get_likes()]
            post_data = {
                "postdate": post.date_utc.strftime("%Y-%m-%d_%H%M%S"),
                "caption": post.caption,
                "caption_mentioned": post.caption_mentions,
                "caption_hashtags": post.caption_hashtags,
                "tagged": post.tagged_users,
                "media_count": post.mediacount,
                "total_likes": post.likes,
                "total_comments": post.comments,
                "liked_by": likers,
                "location": self.get_location(post.location),
                "video_view_count": post.video_view_count,
                "comments": {
                    comment.id: {
                        comment.owner.username: {
                            "text": comment.text,
                            "total_likes": comment.likes_count,
                            "liked_by": ([like.username for like in comment.likes] if comment.likes_count <= 25 else [])
                        }
                    } for com in post_comments for comment in com['postcomment']
                }
            }
            data["posts"][post.shortcode] = post_data
        return data

    def highlights_changed(self, previous_data: dict, current_data: dict, userid: str) -> Dict:
        """ Track media change from highlights """
        # bp()
        previous_highlights = set(previous_data.keys())
        current_highlights = set(current_data.keys())
        new_highlights = list(current_highlights - previous_highlights)
        deleted_highlights = list(previous_highlights - current_highlights)
        for highlight in previous_highlights.intersection(current_highlights):
            previous_stories = previous_data.get(highlight, {})
            current_stories = current_data.get(highlight, {})
            previous_stories_set = set(previous_stories.keys())
            current_stories_set = set(current_stories.keys())
            new_stories = list(current_stories_set - previous_stories_set)
            deleted_stories = list(previous_stories_set - current_stories_set)

            if new_stories:
                logging.info(f"[+] New Stories {new_stories} Found in Highlight '{highlight}'")
                previous_data = self.handle_changes(data=current_data, post_data=previous_data, new=set(new_stories),
                                        deleted=set(), key=highlight, type='stories', userid=userid)
            # Check for deleted stories within the highlight
            if deleted_stories:
                logging.info(f"Deleted Stories {deleted_stories} From Highlight '{highlight}'")
                previous_data = self.handle_changes(data=current_data, post_data=previous_data, new=set(),
                                        deleted=set(deleted_stories), key=highlight, type='stories', userid=userid)

        if new_highlights:
            logging.info(f"[+] New Highlights: {new_highlights} were discovered")
            for new in new_highlights:
                previous_data.update({new: current_data[new]})
        if deleted_highlights:
            logging.info(f"[+] Deleted Highlights: {deleted_highlights} were removed")
            for deleted in deleted_highlights:
                previous_data.pop(deleted)

        return previous_data

    def media_changed(self, current_data: dict, previous_data: dict, userid: str, type: str = "posts") -> Union[bool, Tuple[Set, Set]]:
        """ Track user media change from posts/stories """
        num_current = len(current_data)
        num_previous = len(previous_data)
        if num_current != num_previous:
            logging.info(f"Media {type} has been changed from {num_previous} to {num_current}")
            deleted = set(previous_data.keys()).difference(current_data.keys())
            new = set(current_data.keys()).difference(previous_data.keys())
            changed = [{type: num_current}]
            old_changed = [{type: num_previous}]
            self.save_changes(changed, old_changed, userid)
            return new, deleted
        else:
            logging.info(f"No {type} changes were found")
            return False

    def check_downloaded(self, type: str, dirname: str) -> bool:
        """ Check if media is downloaded """
        dir = Path(Path.cwd().parent.as_posix()+f"/media/{str(self.profile.username)}/{type}/{dirname}/") # type: ignore
        return dir.is_dir()

    def log_new(self, data: dict, type: str):
        """ Log new items """
        for item in data[type]:
            if type == "posts":
                bp()
                logging.info(f"[+] saving post {data[type][item]['caption']}")
            elif type == "highlights":
                logging.info(f"[+] saving highlight {item} with {len(data[type][item])} stories")
            else:
                logging.info(f"[+] saving story {data[type][item]['upload_data']}")

    def mark_changes(self, data: dict, type: str, userid: str) -> None:
        """ Mark/Save Changes from stories/highlights/posts """
        if type == "posts":
            data_file = self.user_file(userid, "postdata")
        else:
            data_file = self.user_file(userid, "storydata")
        post_data = self.read_write(data_file, data=None) or {}
        if not post_data:
            logging.info(f"No {type} metadata was saved yet..")
            self.log_new(data=data, type=type)
            post_data.update(data)
            self.read_write(data_file, post_data, mode='w')
            return
        try: #FIXME Add Highlight media changes.
            # bp()
            if type == 'highlights':
                post_data = self.highlights_changed(previous_data=post_data[type], current_data=data[type],
                                        userid=userid)
            else:
                new, deleted = self.media_changed(data[type], post_data[type], userid, type=type)  # type: ignore # works only for posts and stories
                post_data = self.handle_changes(data=data, post_data=post_data, new=new,
                                                deleted=deleted, key=type, type=type, userid=userid)
            self.read_write(data_file, post_data, mode='w')
        except Exception as _:
            logging.info(f"{type} items are already at their latest")
            return

    def handle_changes(self, data: dict, post_data: dict, new: set,
                       deleted: set, key: str, type: str, userid: str) -> Dict:
        """ Documentation """
        key = key if key != type else type
        print(key)
        bp()
        if new:
            post_data[key].update(data[key])
            for post in list(new):
                if type == 'stories':
                    datetime_str = data[key][post]['upload_date']
                    dt = datetime.strptime(datetime_str, '%Y-%m-%d_%H:%M:%S')
                    item_key = dt.strftime('%A-%m-%d-%Y_%H:%M:%S')
                else:
                    item_key = data[key][post]['caption']
                logging.info(f"{type} item {item_key} has been added to db")
        if deleted:
            for post in list(deleted):
                deleted_post = post_data[key].pop(post)
                if type != "posts":
                    dirname = download_cap = deleted_post['upload_date']
                    dirname = datetime.strptime(dirname, '%Y-%m-%d_%H:%M:%S')
                    dirname = f"story_{dirname.strftime('%Y-%m-%d')}"
                else: dirname = deleted_post['postdate']; download_cap = deleted_post['caption']
                if self.check_downloaded(type=type, dirname=dirname):
                    logging.info(f"Luckily deleted {type} {download_cap} was already downloaded")
                else:
                    logging.info(f"Unlucky deleted {type} {download_cap} was not downloaded before")
                    logging.info("But its metadata is still saved for data processing")
                self.deleted_save(data={post: deleted_post}, userid=userid, type=type)
        return post_data

    def save_changes(self, changes, old_changes, userid):
        """ Save User Changes Into A File """
        user_mark = self.user_file(userid, "changes")
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

    def deleted_save(self, data: dict, userid:str, type: str):
        """ Save deleted posts/stories/highlights metadata """
        dfile = Path(f"~/.config/instman/userdata/{userid}/deleted_media.json").expanduser()
        dfile.touch()
        old_data, _ = self.read_data(dfile, userid)
        if not old_data:
            old_data = {"posts": {}, "stories": {}, "highlights": {}}
        old_data[type].update(data)
        self.read_write(dfile, old_data, mode='w')

    def renew_data(self, data, userid, k, v):
        """ Renew old data once changes were made """
        user_file = self.user_file(userid, "data")
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
        user_file = self.user_file(userid, "data")
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
                Ist.user_data(users, args.ignore_count)
        else:
            Ist.user_data(list(args.user), args.ignore_count)
    elif args.print:
        Ist.get_info(args.user[0])
    elif args.media:
        Ist.list_media(args.user[0], args.highlights, args.stories, args.posts, args.comments, args.download)
    else:
        # profile = Ist.profile_access(args.user[0])
        # print(Ist.get_hashtags(profile))
        # Ist.get_userinfo(profile)
        print("Nothing Checked")
main()
