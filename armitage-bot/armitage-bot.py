#!/usr/bin/env python3

__version__="0.1"

import praw
import requests
import configparser
import sqlite3
import json
import time
import re
import datetime
import threading
from fuzzywuzzy import fuzz
from fuzzywuzzy import process



def pull_arkham_cards(cardrange):
	arkhamdb_api = "http://arkhamdb.com/api/public/card/{}"
	for cardnum in cardrange:
		with sqlite3.connect('armitage.db') as con:
			missing = con.execute("select * from arkham_cards where ID = ?",(cardnum,)).fetchone() == None
			if missing:
				padded_cardnum = "0"+str(cardnum)
				req = requests.get(arkhamdb_api.format(padded_cardnum))
				if req.status_code == 200:
					card_code=req.json()['code']
					card_name=req.json()['name']
					card_url=req.json()['url']
					insert_query = "insert into arkham_cards (ID,name,url) values (?,?,?)"
					cur = con.execute(insert_query,(card_code,card_name,card_url))
					con.commit()
					time.sleep(0.25)
		# cardnum += 1

def build_arkham_dict():
	with sqlite3.connect('armitage.db') as con:
		cur = con.execute("select name,url from arkham_cards")
		all_cards = cur.fetchall()
	arkham_dict = {}
	for card in all_cards:
		arkham_dict[card[0]] = card[1]
	return arkham_dict

def build_netrunner_dict():
	with sqlite3.connect('armitage.db') as con:
		cur = con.execute("select name,url from netrunner_cards")
		all_cards = cur.fetchall()
	arkham_dict = {}
	for card in all_cards:
		arkham_dict[card[0]] = card[1]

def log_comment(comment):
	with sqlite3.connect('armitage.db') as con:
		con.execute("insert into comments (Id) values (?)",(str(comment),))
		con.commit()

def already_replied(comment):
		with sqlite3.connect('armitage.db') as con:
			query_string = "select * from comments where Id = ?"
			cur = con.execute(query_string,(str(comment),))
			return cur.fetchone() != None

def fuzzy_match_card(card_dict,card_name):
	ratio_max = 0
	max_card = ""
	card_name=card_name.lower()
	for i in card_dict.keys():
		fuzz_ratio = fuzz.ratio(card_name,i.lower())
		if fuzz_ratio > ratio_max:
			ratio_max = fuzz_ratio
			max_card = i
	return max_card

def get_ids_by_name(card_name):
	with sqlite3.connect('armitage.db') as con:
		query_string = ("select ID from arkham_cards where name = (?)")
		cur = con.execute(query_string,(card_name,))
		results = cur.fetchall()
	return [i[0] for i in results]

def get_arkham_card_details(card_id):
	arkhamdb_api = "http://arkhamdb.com/api/public/card/{}"
	padded_id = "0"+str(card_id)
	req = requests.get(arkhamdb_api.format(padded_id))
	return req.json()


def build_reply(rjson):
	reply = "**[{}]({})**".format(rjson['name'],rjson['url'])
	if rjson['type_code'] == 'investigator':
		reply += build_investigator(rjson)
	elif rjson['type_code'] == 'asset':
		reply += build_asset_event(rjson)
	elif rjson['type_code'] == 'event':
		reply += build_asset_event(rjson)
	elif rjson['type_code'] == 'skill':
		reply += build_skill(rjson)
	elif rjson['type_code'] == 'enemy':
		reply += build_enemy(rjson)
	elif rjson['type_code'] == 'treachery':
		reply += build_treachery(rjson)
	else:
		pass
		# reply += "    \n"
		# possible_properties = ["faction_name","text"]
		# for p in possible_properties:
		# 	if p in rjson.keys():
		# 		reply += "{}".format(replace_html(rjson[p]))
		# 		reply += "    \n"
	reply = replace_html(reply)
	reply += "\n\n"
	# reply += "    \n"
	return reply


def build_investigator(rjson):
	reply = []
	reply.append(": {}".format(rjson['subname']))
	reply.append("**{}**".format(rjson['faction_name']))
	reply.append("*{}*".format(rjson['traits']))
	reply.append("{}[willpower] {}[intellect] {}[combat] {}[agility]".format(rjson['skill_willpower'],rjson['skill_intellect'],rjson['skill_combat'],rjson['skill_agility']))
	reply.append("Health: {} Sanity: {}".format(rjson['health'],rjson['sanity']))
	reply.append(rjson['text'])
	reply.append("*{}*".format(rjson['flavor']))
	return "    \n".join(r for r in reply)

def build_asset_event(rjson):
	# reply = ["    \n"]
	if 'subname' in rjson.keys():
		reply = [": {}".format(rjson['subname'])]  
	else: 
		reply = ["    "]
	if 'slot' in rjson.keys():
		reply.append("**{}** - {}".format(rjson['type_name'],rjson['slot']))
	else:
		reply.append("**{}**".format(rjson['type_name']))
	reply.append("{}".format(rjson['faction_name']))
	reply.append("*{}*".format(rjson['traits']))
	cost_xp=""
	if 'cost' in rjson.keys():
		cost_xp += "Cost: {} ".format(rjson['cost'])
	if 'xp' in rjson.keys():
		cost_xp += "Level: {} ".format(rjson['xp'])
	if len(cost_xp) != 0:
		reply.append(cost_xp)
	reply.append(rjson['text'])
	if 'flavor' in rjson.keys():
		reply.append("*{}*".format(rjson['flavor']))
	return "    \n".join(r for r in reply)

def build_skill(rjson):
	# reply = ["    \n"]
	reply = ["    "]
	skills = ["skill_willpower","skill_intellect","skill_combat","skill_agility","skill_wild"]
	reply.append("{}".format(rjson['faction_name']))
	reply.append("*{}*".format(rjson['traits']))
	skill_icons=""
	for skill in skills:
		if skill in rjson.keys():
			for sk in range(0,int(rjson[skill])):
				skill_icons += "[{}]".format(skill[6:])
	reply.append(skill_icons)
	reply.append("Level: {}".format(rjson['xp']))
	reply.append(rjson['text'])
	if 'flavor' in rjson.keys():
		reply.append("*{}*".format(rjson['flavor']))
	return "    \n".join(r for r in reply)

def build_enemy(rjson):
	pass

def build_treachery(rjson):
	pass


def replace_arkham_emotes(text):
	emotes = {"willpower":"willpower",
			"intellect":"intellect",
			"combat":"combat",
			"agility":"agility",
			"skull":"skull",
			"cultist":"cultist",
			"brokentablet":"tablet",
			"elderthing":"elder_thing",
			"eldersign":"elder_sign",
			"autofail":"auto_fail",
			"wild":"wild",
			"perinvestigator":"per_investigator"}
	for e in emotes.keys():
			re_str = r"""\[{}\]""".format(emotes[e])
			emote_str = "[](/{})".format(e)
			text = re.sub(re_str,emote_str,text)
	return text

def replace_html(text):
	text = re.sub(r"""(<\/*b>)""","**",str(text))
	text = re.sub(r"""(<\/*i>)""","*",str(text))
	return text

def sieve_cards_from_comment(comment_body):
	return re.findall(r"""\?([A-z.\"][A-z0-9'.:! \"]+)*\?""",comment_body)

def watch_comments():
	sub = "sandboxtest"
	for comment in r.subreddit(sub).stream.comments():
		reply = ""
		if comment.created_utc > (time.time() - 300) and not already_replied(comment):
			possible_cards = sieve_cards_from_comment(comment.body)
			if possible_cards:
				for fuzzy_name in possible_cards:
					card_name = fuzzy_match_card(arkham_dict,fuzzy_name)
					for cid in get_ids_by_name(card_name):
						rjson = get_arkham_card_details(cid)
						reply += build_reply(rjson)
						reply = replace_arkham_emotes(reply)
				reply_to_comment(comment,reply)

def watch_submissions():
	sub = "sandboxtest"
	for comment in r.subreddit(sub).stream.submissions():
		reply = ""
		if comment.created_utc > (time.time() - 300) and not already_replied(comment):
			possible_cards = sieve_cards_from_comment(comment.selftext)
			if possible_cards:
				for fuzzy_name in possible_cards:
					card_name = fuzzy_match_card(arkham_dict,fuzzy_name)
					for cid in get_ids_by_name(card_name):
						rjson = get_arkham_card_details(cid)
						reply += build_reply(rjson)
						reply = replace_arkham_emotes(reply)
				reply_to_comment(comment,reply)

def reply_to_comment(comment,reply):
	print("trying to reply...")
	try:
		comment.reply(reply)
		log_comment(comment)
		print(reply)
	except Exception as e:
		print("reply error:")
		with open('armitage.log','a') as log:
			log.write(str(datetime.datetime) + " " + str(e))
		print(e)

r = praw.Reddit(site_name="armitage")
arkham_dict = build_arkham_dict()

if __name__ == "__main__":
	try:
		threading.Thread(target=watch_comments).start()
		threading.Thread(target=watch_submissions).start()
	except Exception as e:
		with open('armitage.log','a') as log:
			log.write(str(datetime.datetime) + " " + str(e))
		print(e)
