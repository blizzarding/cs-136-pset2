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
        logging.debug("%s again.  It's round %d." % (self.id, round))
        # One could look at other stuff in the history too here.
        # For example, history.downloads[round-1] (if round != 0, of course)
        # has a list of Download objects for each Download to this peer in
        # the previous round.

        uploads = []
        download_from = {}

        if round != 0:
            prev_round = history.downloads[round - 1]
            for download in prev_round:
                if download.to_id == self.id:
                    from_id = download.from_id
                    if from_id not in download_from.keys():
                        download_from[from_id] = download.blocks
                    else:
                        download_from[from_id] += download.blocks

        bw_opt_unblock_share = 0.1
        total_bw = self.up_bw

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
        else:
            logging.debug("Still here: uploading to a random peer")
            # change my internal state for no reason
            self.dummy_state["cake"] = "pie"

            requesters = [request.requester_id for request in requests]
            upload_to = []

            for requester in requesters:
                if requester in download_from.keys():
                    upload_to.append(requester)

            total_blocks = 0
            for peer_id in upload_to:
                total_blocks += download_from[peer_id]

            for peer_id in upload_to:
                share = (1 - bw_opt_unblock_share) * (float(download_from[peer_id]) / (total_blocks))
                uploads.append(Upload(self.id, peer_id, int(share * total_bw)))
                requesters.remove(peer_id)
            
            if len(requesters) > 0:
                opt_unblock = random.choice(requesters)
                uploads.append(Upload(self.id, opt_unblock, int(bw_opt_unblock_share * total_bw)))
            
        return uploads

        # trying helen/jessica's
        '''
        round = history.current_round()

        if len(requests) == 0:
            logging.debug("No one wants my pieces!")
            chosen = []
            bws = []
            uploads = []
        else:
            logging.debug("Still here: uploading to a random peer")
            # change my internal state for no reason
            self.dummy_state["cake"] = "pie"

            requesters = {}
            for r in requests:
                requesters[r.requester_id] = 0
            
            for download in history.downloads[round - 1]:
                if download.from_id in requesters:
                    requesters[download.from_id] += download.blocks

            partners = {k : v for k, v in requesters.items() if v > 0}
            newbies = {k : v for k, v in requesters.items() if v == 0}

            # if none of the requesters are previous partners, choose someone randomly to allocate all bandwidth to
            if len(newbies) == len(requesters):
                opt_unblock = random.choice([newbies.keys()])
                uploads = [Upload(self.id, opt_unblock, self.up_bw)]
            else:
                chosen = [partners.keys()]
                nonchosen = [newbies.keys()]
                bws = []
                total_prev_downloads = sum([partners.values()])

                if len(partners) == len(requesters):
                    for partner in chosen:
                        share = requesters[partner] / total_prev_downloads
                        bws.append(int(share * (self.up_bw)))
                else:
                    for partner in chosen:
                        share = requesters[partner] / total_prev_downloads
                        bws.append(int(0.9 * share * (self.up_bw)))
                    opt_unblock = random.choice(nonchosen)
                    chosen.append(opt_unblock)
                    bws.append(self.up_bw - sum(bws))
                
                uploads = [Upload(self.id, peer_id, bw) for (peer_id, bw) in zip(chosen, bws)]

        return uploads
        '''