#!/usr/bin/python

# This is a dummy peer that just illustrates the available information your peers 
# have available.

# You'll want to copy this file to AgentNameXXX.py for various versions of XXX,
# probably get rid of the silly logging messages, and then add more logic.

import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer

class RealStd(Peer):
    def post_init(self):
        print(("post_init(): %s here!" % self.id))
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
        self.optimistic_unblock = None
        # can define additional global attributes here
        # can track who you're currently optimistically unblocking, can also check round #, how many times you've uploaded to, etc.
    
    def requests(self, peers, history):
        """
        peers: available info about the peers (who has what pieces)
        history: what's happened so far as far as this peer can see

        returns: a list of Request() objects

        This will be called after update_pieces() with the most recent state.
        """
        needed = lambda i: self.pieces[i] < self.conf.blocks_per_piece
        needed_pieces = list(filter(needed, list(range(len(self.pieces)))))
        np_set = set(needed_pieces)  # sets support fast intersection ops.


        logging.debug("%s here: still need pieces %s" % (
            self.id, needed_pieces))

        logging.debug("%s still here. Here are some peers:" % self.id)
        for p in peers:
            logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))

        logging.debug("And look, I have my entire history available too:")
        logging.debug("look at the AgentHistory class in history.py for details")
        logging.debug(str(history))

        requests = []   # We'll put all the things we want here
        # Symmetry breaking is good...
        random.shuffle(needed_pieces)
        
        # Sort peers by id.  This is probably not a useful sort, but other 
        # sorts might be useful
        peers.sort(key=lambda p: p.id)

        '''
        when you're requesting, you request rarest first
        you request for pieces -> someone only has access to a piece if they have all blocks
        you send a request for everything you can, with the bandwidth you have available
        '''
        # rarity is based off of pieces, not blocks
        # in peer, there's something about available pieces
        # you go through all peers, see all avail ones, manually count through how many of each block is avail, and then 
        # you can request multiple pieces from the same peer (request all the time as much as possible)
        # you send requests in order of rarity within peers -> you request from everyone, and everyone can upload a different amount to you (but all in the same round)
        avail = dict()
        for peer in peers:
            for piece in peer.available_pieces:
                avail.setdefault(piece, [])
                avail[piece].append(peer.id)
        rarity = {}
        for i in sorted(avail, key=lambda i: len(avail[i])):
            rarity[i] = len(avail[i])

        # request all available pieces from all peers!
        # (up to self.max_requests from each)
        for peer in peers:
            av_set = set(peer.available_pieces)
            isect = list(av_set.intersection(np_set))
            n = min(self.max_requests, len(isect))

            random.shuffle(isect)
            isect_sorted = sorted(isect, key=lambda x: rarity[x])

            # More symmetry breaking -- ask for random pieces.
            # This would be the place to try fancier piece-requesting strategies
            # to avoid getting the same thing from multiple peers at a time.
            for piece_id in random.sample(isect_sorted, n):
                if peer.id in avail[piece_id]:
                    start_block = self.pieces[piece_id]
                    r = Request(self.id, peer.id, piece_id, start_block)
                    requests.append(r)

            #
                # aha! The peer has this piece! Request it.
                # which part of the piece do we need next?
                # (must get the next-needed blocks in order)
                
                #r = Request(self.id, peer.id, piece_id, start_block)
                #requests.append(r)
        return requests

        # for peer in peers:
        #   get intersection
        #   shuffle intersection
        #   sort interesection by rarity
        #   request first n pieces from this list

    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round -> list of requester objects, within each can .requester_id
        peers -- available info about all the peers
        history -- history for all previous rounds

        returns: list of Upload objects.

        In each round, this will be called after requests().
        """

        r = history.current_round()
        logging.debug("%s again.  It's round %d." % (
            self.id, r))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.
        preference = []
        requesters = [request.requester_id for request in requests]
        uploads = []
        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading to a random peer")
            # change my internal state for no reason
            self.dummy_state["cake"] = "pie"

            '''to be deleted:'''
            # We're talking about one specific player p
            # goal is to build up download_from which will index by peer ids so that we can
            # eventually sort by avg downloaded from rates (peers upload to RC)
            # download_from = [(0, 0) for i in range(len(peers))] # downloading from peers for the past two rounds
            '''End of bad code'''

            if 1 <= len(requests) <= 3:
                bw_short = even_split(self.up_bw, len(requests))
                for i, request in enumerate(requests):
                    uploads.append(Upload(self.id, request.requester_id, bw_short[i]))
            else:
                download_from = {}
                rounds = history.downloads[-2:]
                for round in rounds:
                    for download in round:
                        if download.from_id not in download_from.keys():
                            download_from[download.from_id] = download.blocks
                        else:
                            download_from[download.from_id] += download.blocks

                download_from_list = list(download_from.items())
                random.shuffle(download_from_list)
                preference = (sorted(download_from_list, key=lambda item: item[1], reverse = True))

                bws = even_split(self.up_bw, 4)
                uploaded = 0
                for interested in download_from_list:
                    if interested in requesters:
                        uploads.append(Upload(self.id, interested, bws[uploaded]))
                        requesters.remove(interested)
                        uploaded += 1
                    if uploaded == 3:
                        break
                while uploaded < 3:
                    next = random.choice(requesters)
                    uploads.append(Upload(self.id, next, bws[uploaded]))
                    requesters.remove(next)
                    uploaded += 1

                if r % 3 == 0 and r != 0:
                    if len(requesters)!=0:
                        self.optimistic_unblock = random.choice(requesters)
                if r >= 3 and self.optimistic_unblock != None and (self.optimistic_unblock in requesters):
                    uploads.append(Upload(self.id, self.optimistic_unblock, bws[3]))                        
             
        return uploads
                

        #         # [(peer_id, numblocks), (peer_id, numblocks), (peer_id, numblocks)]

        #     '''TODO: LIZ FINISH OPTIMISTIC UNBLOCKING'''
        #     # insert logic for defining the optimistic unblock here
        #     if round == 0:
        #             chosen = random.shuffle(requesters)[:4]
        #     else:
        #         if (len(preference) > 3):
        #             if (round%3) == 0:
        #                 self.optimistic_unblock = random.choice(preference[3:]) 
        #                     # requests is the list of people who requested from you
        #         optimistic_unblock = self.optimistic_unblock
        #         chosen = [item[0] for item in preference[:3]] + [optimistic_unblock]

        #     # Evenly "split" my upload bandwidth among the 3 chosen requesters and the 1 optimistic unblock
        #     '''how do we deal with things that aren't dividable? -> you divide as best as possible and prefer to give more to those earlier in the rankings'''
        #     if chosen:
                
        #         uploads = [Upload(self.id, peer_id, bw)
        #             for (peer_id, bw) in zip(chosen, bws)]
        #     else:
        #         uploads = []

        # # create actual uploads out of the list of peer ids and bandwidths
        

        # # for reference client, distribute bandwidth evenly

        # # everyone who sent request for piece is interested peers [requests]
        # # optimistic unblock: if get, then stay for 3 rounds max (or until they don't need it anymore)
        # # give them the option to have that spot for the next three rounds -> discrepancies
        # # have global var for the ID of the unblocked person -> 

        # # do we need to filter peers by interested peers, i.e., those that want something from ref client?

        # # order in decreasing order of av download rate received from peers, breaking ties at random
        # # and excluding any peers that have not sent any data -> we already don't have peers that haven't sent any data

        # # you take the maximum 3 and you put them in your uploads method (this is all in uploads)

        # # you prefer to upload to people who upload to you
        # # you have 3 normal spots in your reference client to upload to people, and there's one optimistic

        # # to unblock someone, you put their ID and their bandwidth in the uploads list

        
