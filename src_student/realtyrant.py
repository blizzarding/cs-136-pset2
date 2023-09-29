#!/usr/bin/python

# This is a dummy peer that just illustrates the available information your peers 
# have available.

# You'll want to copy this file to AgentNameXXX.py for various versions of XXX,
# probably get rid of the silly logging messages, and then add more logic.

# OVERALL LOGIC FOR BITTYRANT
# exploit who is optimal to give to, so if someone is really generous, help them less because they'll still keep uploading to us
# for each peer, estimate 
# 1) if they unblock us, how much bandwidth will they give us? -> d_i
# 2) how much we need to give them for them to unblock us? -> u_i
# after every round, compare d_i/u_i for each peer i 
#     keep D dict and U dict for all peers and update after every round


# ESTIMATING D_i and U_i
# Estimating d_i:
# CASE ONE: Peer i has never unblocked us before. make some assumptions about peer i 
#         side note: (for tourney, can make "better" assumptions)
# for tyrant, we can assume peer i is std client, i.e. they split bandwidth into 4 parts, and
# assume their upload rate is equal to their download rate (since std. client is ~ tft)
# d_i = ((total # of pieces they have)/(total # of rounds past))/4

#CASE TWO: if peer i has unblocked us before, look at most recent time they've unblocked us, and set d_i to that value

# Estimating u_i: how much do we have to give them?
# Initialize u_i to some capacity. Book says to set to estimate capacity, e.g. 16 or max bandwidth/4
# Case 1: If we unblock them, but they don't unblock us, u_i = 1.2 u_i -> increase u_i by 20%
# Case 2: If they unblock us for previous r rounds in a row, u_i = (1- gamma)^r u_i where gamma = 0.1 and r = 3
# Those parameters can be changed to optimize (or change gamme and r for tourney)
# In all other cases, don't change u_i

# for uploads:
# Requests overview for BitTyrant
# Requests () Method
# Look at all the requests 
# get d_i/u_i for each peer in requests, rank in decreasing order
# give the peer with the most d_i/u_i u_i. Then iterate through sorted peers and give them all their u_i
# give the last person whatever you have left

import random
import logging

from messages import Upload, Request
from util import even_split
from peer import Peer

class RealTyrant(Peer):
    def post_init(self):
        print(("post_init(): %s here!" % self.id))
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
        self.d = dict()
        self.u = dict()
        self.ratio = dict()
        self.unblocked_me = dict()
    
    # Requests overview for BitTyrant
    # Requests () Method
    # Look at all the requests 
    # get d_i/u_i for each peer in requests, rank in decreasing order
    # give the peer with the most d_i/u_i u_i. Then iterate through sorted peers and give them all their u_i
    # give the last person whatever you have left

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


    def uploads(self, requests, peers, history):
        """
        requests -- a list of the requests for this peer for this round
        peers -- available info about all the peers
        history -- history for all previous rounds

        returns: list of Upload objects.

        In each round, this will be called after requests().
        """

        
        round = history.current_round()
        requesters = [request.requester_id for request in requests]
        logging.debug("%s again.  It's round %d." % (
            self.id, round))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.
        uploads = []
        if round == 0:
            for peer in peers:
                self.u[peer.id] = self.up_bw / 4
                self.d[peer.id] = len(peer.available_pieces) / 4
                self.unblocked_me[peer.id] = 0
        unblocked = []
        upload_bws = []

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading to a random peer")
            # change my internal state for no reason
            self.dummy_state["cake"] = "pie"

            gamma = 0.1
            r = 3
            alpha = 0.2

            for peer in peers:
                self.ratio[peer.id] = self.d[peer.id] / self.u[peer.id]
            
            limit = self.up_bw

            while limit > 0 and len(self.ratio) > 0:
                top_ratio = max(list(self.ratio.values()))
                at_top = []
                for k in self.ratio:
                    if self.ratio[k] == top_ratio:
                        at_top.append(k)
                upload_to = random.choice(at_top)

                if limit - self.u[upload_to] > 0 and upload_to in requesters:
                    unblocked.append(upload_to)
                    upload_bws.append(self.u[upload_to])
                    limit -= self.u[upload_to] 
                
                self.ratio.pop(upload_to)
        
            if round != 0:
                previous = history.downloads[round - 1]
                past_downloads = {}

                # here, we look at our downloads from peers in previous round
                for download in previous:
                    d = download.from_id
                    if d not in past_downloads:
                        past_downloads[d] = download.blocks
                    else:
                        past_downloads[d] += download.blocks

                # here, we look at who unblocked us in last round
                for peer in peers:
                    p = peer.id
                    if p in past_downloads:
                        self.unblocked_me[p] += 1
                    else:
                        self.unblocked_me[p] = 0
                
                for peer in unblocked:
                    if round > 0:
                        if self.unblocked_me[peer] == 0:
                            self.u[peer] = self.u[peer] * (1+ alpha)

                            for p in peers:
                                if p.id == peer:
                                    self.d[peer] = len(p.available_pieces) / 4
                    
                    else:
                        self.d[peer] = past_downloads[peer]

                        if self.unblocked_me[peer] >= r:
                            self.u[peer] = self.u[peer] * (1-gamma)
            
        for i in range(len(unblocked)):
            uploads.append(Upload(self.id, unblocked[i], upload_bws[i]))
            
        return uploads
