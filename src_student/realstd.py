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
        self.optimistic_unblock = ["", 0]
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
        for peer in peers:
            for piece in peer.available_pieces:


        # request all available pieces from all peers!
        # (up to self.max_requests from each)
        for peer in peers:
            av_set = set(peer.available_pieces)
            isect = av_set.intersection(np_set)
            n = min(self.max_requests, len(isect))
            # More symmetry breaking -- ask for random pieces.
            # This would be the place to try fancier piece-requesting strategies
            # to avoid getting the same thing from multiple peers at a time.
            for piece_id in random.sample(isect, n):
                # aha! The peer has this piece! Request it.
                # which part of the piece do we need next?
                # (must get the next-needed blocks in order)
                start_block = self.pieces[piece_id]
                r = Request(self.id, peer.id, piece_id, start_block)
                requests.append(r)

        return requests

    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round -> list of requester objects, within each can .requester_id
        peers -- available info about all the peers
        history -- history for all previous rounds

        returns: list of Upload objects.

        In each round, this will be called after requests().
        """

        round = history.current_round()
        logging.debug("%s again.  It's round %d." % (
            self.id, round))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.

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
            # goal is to build up avg_download_from which will index by peer ids so that we can
            # eventually sort by avg downloaded from rates (peers upload to RC)
            # avg_download_from = [(0, 0) for i in range(len(peers))] # downloading from peers for the past two rounds
            '''End of bad code'''

            requesters = [request.requester_id for request in requests]
            avg_download_from = {}
            rounds = history.downloads[-2:]
            

            for round in rounds:
                for download in round:
                    if download.from_id not in avg_download_from.keys():
                        avg_download_from[download.from_id] = download.blocks
                    else:
                        avg_download_from[download.from_id] += download.blocks

            # random.shuffle(rounds) # randomize order of lists; we randomize and then sort to break ties randomly!
            # # either randomize requesters or we randomize rounds

            preference = (sorted(avg_download_from.items(), key=lambda item: item[1], reverse = True))[:3]
            # [(peer_id, numblocks), (peer_id, numblocks), (peer_id, numblocks)]
        
        chosen = [item[0] for item in preference]

        # insert logic for defining the optimistic unblock here
        optimistic_unblock = self.optimistic_unblock
        request = random.choice(requests) # requests is the list of people who requested from you
        
        # Evenly "split" my upload bandwidth among the 3 chosen requesters and the 1 optimistic unblock
        '''how do we deal with things that aren't dividable? -> you divide as best as possible and prefer to give more to those earlier in the rankings'''
        bws = even_split(self.up_bw, len(chosen + 1))

        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
            
        return uploads

        '''OLD CODE'''
        # avg_download_from = {}
        # rounds = self.AgentHistory.downloads[-2:] # for the reference client, the list of downloads (and who we're downloading from) for the last two rounds
        # for round in rounds:
        #     for download in round:
        #         if download.from_id not in avg_download_from.keys():
        #             avg_download_from[download.from_id] = download.blocks
        #         else:
        #             avg_download_from[download.from_id] += download.blocks
        '''END OF OLD CODE'''
        

        # for reference client, distribute bandwidth evenly

        # everyone who sent request for piece is interested peers [requests]
        # optimistic unblock: if get, then stay for 3 rounds max (or until they don't need it anymore)
        # give them the option to have that spot for the next three rounds -> discrepancies
        # have global var for the ID of the unblocked person -> 

        # do we need to filter peers by interested peers, i.e., those that want something from ref client?
        
        

        # order in decreasing order of av download rate received from peers, breaking ties at random
        # and excluding any peers that have not sent any data -> we already don't have peers that haven't sent any data

        # you take the maximum 3 and you put them in your uploads method (this is all in uploads)

        # you prefer to upload to people who upload to you
        # you have 3 normal spots in your reference client to upload to people, and there's one optimistic

        # to unblock someone, you put their ID and their bandwidth in the uploads list

        
