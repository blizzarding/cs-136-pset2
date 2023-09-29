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

class RealPropShare(Peer):
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
        # np_set = set(needed_pieces)  # sets support fast intersection ops.


        logging.debug("%s here: still need pieces %s" % (
            self.id, needed_pieces))

        logging.debug("%s still here. Here are some peers:" % self.id)
        for p in peers:
            logging.debug("id: %s, available pieces: %s" % (p.id, p.available_pieces))

        logging.debug("And look, I have my entire history available too:")
        logging.debug("look at the AgentHistory class in history.py for details")
        logging.debug(str(history))

        # Symmetry breaking is good...
        random.shuffle(needed_pieces)
        
        # Sort peers by id.  This is probably not a useful sort, but other 
        # sorts might be useful
        # peers.sort(key=lambda p: p.id)

        requests = []   # We'll put all the things we want here

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
        for piece in needed_pieces:
            for peer in peers:
                if piece in peer.available_pieces:
                    if piece in avail.keys():
                        avail[piece] += 1
                    else:
                        avail[piece] = 1

        rarity = list(dict(sorted(avail.items(), key=lambda x: x[1])).keys())
        random.shuffle(peers)
        #for i in sorted(avail, key=lambda i: len(avail[i])):
            # rarity[i] = len(avail[i])

        # request all available pieces from all peers!
        # (up to self.max_requests from each)
        for peer in peers:
            av_list = list(peer.available_pieces)
            # find intersection
            isect = [piece for piece in av_list if piece in needed_pieces]
            n = min(self.max_requests, len(isect))

            # randomize to break ties
            random.shuffle(isect)
            isect_sorted = sorted(isect, key=lambda x: rarity.index(x) if x in rarity else len(rarity))

            # More symmetry breaking -- ask for random pieces.
            # This would be the place to try fancier piece-requesting strategies
            # to avoid getting the same thing from multiple peers at a time.
            for i in range(n):
                start_block = self.pieces[isect_sorted[i]]
                r = Request(self.id, peer.id, isect_sorted[i], start_block)
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
        logging.debug("%s again.  It's round %d." % (
            self.id, round))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.

        requesters = [request.requester_id for request in requests]
        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
            uploads = []
        else:
            logging.debug("Still here: uploading to a random peer")

            interested_peers = dict()

            for r in requesters:
                interested_peers[r] = 0

            for download in history.downloads[round - 1]:
                if download.from_id in interested_peers:
                    interested_peers[download.from_id] += download.blocks

            partners = {key : val for key, val in interested_peers.items()
                   if val > 0}
            newbies = {key : val for key, val in interested_peers.items()
                   if val == 0}
           

            if len(newbies) == len(interested_peers):
                lucky = random.choice(list(newbies.keys()))
                uploads = [Upload(self.id, lucky, self.up_bw)]
            
            else:
                chosen = list(partners.keys())
                other = list(newbies.keys())
                bws = []

                if len(partners) == len(interested_peers):
                    for peer in chosen:
                        ratio = (interested_peers[peer])/(sum(list(partners.values())))
                        bws.append(int(ratio*(self.up_bw)))
                else:
                    for peer in chosen:
                        ratio = partners[peer]/(sum(list(partners.values())))
                        bws.append(int(ratio*0.9*(self.up_bw)))
                    
                    other_rand = random.choice(other)
                    chosen.append(other_rand)
                    total_bw = sum(bws)
                    bws.append(self.up_bw - total_bw)

                
                # create actual uploads out of the list of peer ids and bandwidths
                uploads = [Upload(self.id, peer_id, bw)
                    for (peer_id, bw) in zip(chosen, bws)]  
                
        return uploads
















