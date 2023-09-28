#!/usr/bin/python

# This is a dummy peer that just illustrates the available information your peers 
# have available.

# You'll want to copy this file to AgentNameXXX.py for various versions of XXX,
# probably get rid of the silly logging messages, and then add more logic.

# OVERALL LOGIC FOR BITTYRANT
# exploit who is optimal to give to, so if someone is really generous, help them less because they'll still keep uploading to us
# for each peer, estimate 
# 1) if they unblock us, how much bandwidth will they give us? -> d_i
# 2) how much we need to give them for them to unbloc us? -> u_i
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
        requests -- a list of the requests for this peer for this round
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

            request = random.choice(requests)
            chosen = [request.requester_id]
            # Evenly "split" my upload bandwidth among the one chosen requester
            bws = even_split(self.up_bw, len(chosen))

        # create actual uploads out of the list of peer ids and bandwidths
        uploads = [Upload(self.id, peer_id, bw)
                   for (peer_id, bw) in zip(chosen, bws)]
            
        return uploads
