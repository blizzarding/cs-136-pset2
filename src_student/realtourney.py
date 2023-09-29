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

class RealTourney(Peer):
    def post_init(self):
        print(("post_init(): %s here!" % self.id))
        self.dummy_state = dict()
        self.dummy_state["cake"] = "lie"
    
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

        '''MAKE TOURNEY REQUESTS RAREST FIRST'''

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

        r = history.current_round()
        logging.debug("%s again.  It's round %d." % (self.id, r))
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

                # change # of rounds
                if r % 3 == 0 and r != 0:
                    if len(requesters)!=0:
                        self.optimistic_unblock = random.choice(requesters)
                if r >= 3 and self.optimistic_unblock != None and (self.optimistic_unblock in requesters):
                    uploads.append(Upload(self.id, self.optimistic_unblock, bws[3]))                        
             
        return uploads