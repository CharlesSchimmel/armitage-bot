#!/usr/bin/env python3

__name__="armitage-bot"
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
		with sqlite3.connect('arkham.db') as con:
			missing = con.execute("select * from cards where ID = ?",(cardnum,)).fetchone() != None
			if not missing:
				padded_cardnum = "0"+str(cardnum)
				req = requests.get(arkhamdb_api.format(padded_cardnum))
				if req.status_code == 200:
					card_code=req.json()['code']
					card_name=req.json()['name']
					card_url=req.json()['url']
					print("inserting {} {} {}".format(card_code,card_name,card_url))
					insert_query = "insert into cards (ID,name,url) values (?,?,?)"
					cur = con.execute(insert_query,(card_code,card_name,card_url))
					con.commit()
					time.sleep(0.25)
		# cardnum += 1

def build_arkham_dict():
	with sqlite3.connect('arkham.db') as con:
		cur = con.execute("select name,url from cards")
		all_cards = cur.fetchall()
	arkham_dict = {}
	for card in all_cards:
		arkham_dict[card[0]] = card[1]
	return arkham_dict

def build_netrunner_dict():
	with sqlite3.connect('arkham.db') as con:
		cur = con.execute("select name,url from cards")
		all_cards = cur.fetchall()
	arkham_dict = {}
	for card in all_cards:
		arkham_dict[card[0]] = card[1]

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
	with sqlite3.connect('arkham.db') as con:
		query_string = ("select ID from cards where name = (?)")
		cur = con.execute(query_string,(card_name,))
		results = cur.fetchall()
	return [i[0] for i in results]

def get_card_details(card_id):
	arkhamdb_api = "http://arkhamdb.com/api/public/card/{}"
	possible_properties = ["name","type_name","cost","xp","faction_name","slot","traits","text"]
	padded_id = "0"+str(card_id)
	req = requests.get(arkhamdb_api.format(padded_id))
	for p in possible_properties:
		if p in req.json().keys():
			print("{}: {}".format(p,req.json()[p]))

def sieve_cards_from_comment(comment):
    return re.findall(r"""\?([A-z]+\s*[A-z]\w+\s*)*\?""",comment)

comment = "just talking about ?roland? and maybe ?shriveling?"
for fuzzy_name in sieve_cards_from_comment(comment):
	card_name = fuzzy_match_card(build_arkham_dict(),fuzzy_name)
	for cid in get_ids_by_name(card_name):
		get_card_details(cid)
