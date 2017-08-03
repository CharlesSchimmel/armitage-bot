#!/usr/bin/env python3

__version__="0.1"

import praw
import requests
import configparser
import sqlite3
import json
import time
import re
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
	possible_properties = ["name","type_name","cost","xp","faction_name","slot","traits","text","url"]
	padded_id = "0"+str(card_id)
	req = requests.get(arkhamdb_api.format(padded_id))
	reply = ""
	for p in possible_properties:
		if p in req.json().keys():
			reply += "{}: {}".format(p,replace_html(req.json()[p]))
			reply += "\n"
	return reply

def replace_html(text):
	text = str(text)
	return re.sub(r"""(<\/*b>)""","*",text)

def sieve_cards_from_comment(comment_body):
	return re.findall(r"""\?([A-z0-9'.! \"]+)*\?""",comment_body)

def watch_comments():
	sub = "bottest"
	for comment in r.subreddit(sub).stream.comments():
		reply = ""
		if comment.created_utc > (time.time() - 120) and not already_replied(comment):
			possible_cards = sieve_cards_from_comment(comment.body)
			if possible_cards:
				for fuzzy_name in possible_cards:
					card_name = fuzzy_match_card(arkham_dict,fuzzy_name)
					for cid in get_ids_by_name(card_name):
						reply += get_arkham_card_details(cid)
				reply_to_comment(comment,reply)

def reply_to_comment(comment,reply):
	log_comment(comment)
	try:
		comment.reply(reply)
		print(reply)
	except Exception as e:
		print("reply error:")
		print(e)

r = praw.Reddit(site_name="armitage",)
arkham_dict = build_arkham_dict()

if __name__ == "__main__":
	try:
		watch_comments()
	except Exception as e:
		print(e)
