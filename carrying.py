r"""



AUTHORS:

- BALAZS STRENNER (2017-07-30): initial version


"""

# *****************************************************************************
#       Copyright (C) 2017 Balazs Strenner <strennerb@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#                  http://www.gnu.org/licenses/
# *****************************************************************************


# from train_track import TrainTrack
from sage.structure.sage_object import SageObject
from constants import LEFT, RIGHT, START, END
from sage.all import vector
import numpy as np
from train_track import SMALL_COLLAPSIBLE
from train_track0 import TrainTrack

# TODO: make this an inline function in Cython.
to_index = TrainTrack._to_index


def is_smaller_or_equal(array1, array2):
    """Decide if all entries of the first array are less than or equal the
    corresponding entries of the second array.
    """
    assert(array1.size == array2.size)
    return all(array2-array1 >= 0)
    # for i in range(array1.size):
    #     if array1[i] > array2:
    #         return False
    # return True


def is_smaller(array1, array2):
    """Decide if all entries of the first array are less than the
    corresponding entries of the second array.
    """
    assert(array1.size == array2.size)
    return all(array2-array1 > 0)
    # for i in range(array1.size):
    #     if array1[i] > array2:
    #         return False
    # return True


def is_equal(array1, array2):
    """Decide if all entries of the first array equal corresponding entries of the
    second array.

    """
    assert(array1.size == array2.size)
    return all(array2 == array1)
    # for i in range(array1.size):
    #     if array1[i] > array2:
    #         return False
    # return True


class CarryingMap(SageObject):
    """
    A carrying relationship between two train tracks.
    """
    def __init__(self, large_tt, small_tt,
                 train_paths,
                 half_branch_map,
                 hb_between_branches,
                 cusp_index_offset,
                 cusp_map):
        """l = number of branches of the large train track
        s = number of branches of the small train track
        c = number of cusps of the small train track

        INPUT:

        - ``large_tt`` -- the carrying train track

        - ``small_tt`` -- the carried train track

        - ``train_paths`` -- A 2D array whose rows are (almost) measures
        corresponding to the branches of the small train track and the cusp
        paths. Shape: (s+c, l).

        - ``half_branch_map`` -- A 2D array with two rows. The first row
        contains the image half-branches (in the large train track) of
        startings of the branches and cusp paths of the small train track. The
        second row contains the images of the endings of the branches and cusp
        paths the small train track. Shape: (2, s+c).

        - ``hb_between_branches`` -- A 3D array consisting of two 2D arrays.
        The first one is for starting half-branches, the second is for ending
        half-branches. For each, rows correspond to half-branches of the train
        paths and the entries of the row store the position of the half-branch
        all branches and cusp paths. Shape: (2, s+c, s+c).

        - ``cusp_index_offset`` -- a positive integer, usually ``s``. The paths
        in ``train_paths`` correspond to branch paths for indices less than
        ``cusp_index_offset`` and to cusp paths for indices at least
        ``cusp_index_offset``. Similarly for ``half_branch_map`` and the 2nd
        and 3rd axes of ``hb_between_branches``.

        - ``cusp_map`` -- A 1D array specifying the image of any cusp in the
          small train track in the large train track.

        """
        self._large_tt = large_tt
        self._small_tt = small_tt
        self._train_paths = train_paths
        self._half_branch_map = half_branch_map
        self._hb_between_branches = hb_between_branches
        self._cusp_index_offset = cusp_index_offset
        self._cusp_map = cusp_map

    def _path_index(self, typ, index):
        """
        """
        a = 0 if index > 0 else 1
        if typ == BRANCH:
            return (a, abs(index)-1)
        elif typ == CUSP:
            return (a, abs(index) - 1 + self._cusp_index_offset)

    def append(self, typ1, append_to_idx, typ2, appended_path_idx):
        """Update the carrying data when a train path is appended to another.

        
        """
        append_to = self._path_index(typ1, -append_to_idx)
        appended = self._path_index(typ2, -appended_path_idx)
        self._train_paths[append_to[1]] += \
            self._train_paths[appended[1]]
        self._half_branch_map[append_to] = \
            self._half_branch_map[appended]
        self._hb_between_branches[:, :, append_to[1]] += \
            self._hb_between_branches[:, :, appended[1]]
        self._hb_between_branches[append_to] = \
            self._hb_between_branches[appended]

    def add_to_hb_between_branches(self, typ1, add_to_idx,
                                   typ2, added_idx):
        """Add 1 to the count of a branch on the left of a half-branch.

        We usually need to call this method after self.append(), since that
        method simply sets the _hb_between_branches of two branches the same,
        but one of them is to the left of the other. 
        """
        add_to = self._path_index(typ1, add_to_idx)
        added = self._path_index(typ2, added_idx)
        self._hb_between_branches[add_to][added[1]] += 1

    @classmethod
    def identity_map(cls, train_track):
        """Create a carrying map of a train track by itself.

        The large train track is the input train track, the small train track
        is a new copy.

        """
        # TODO rewrite this
        tt = train_track
        max_num_branches = tt.num_branches_if_made_trivalent()
        assert(len(tt.branches()) <= max_num_branches)

        # Identity array of arbitrary-precision Python ints.
        # Keep in mind that we fill in ones also in the rows that are not
        # actually branches.
        train_paths = np.identity(max_num_branches, dtype=object)

        half_branch_map = np.zeros((2, max_num_branches), dtype=np.int)
        for br in tt.branches():
            half_branch_map[START, br-1] = br
            half_branch_map[END, br-1] = -br

        # Initially all half-branches are at position 0 between any other
        # branchpath.
        hb_between_branches = np.zeros((2, max_num_branches, max_num_branches),
                                       dtype=object)

        max_num_switches = tt.num_switches_if_made_trivalent()

        # The number of cusps equals the number of switches for trivalent train
        # tracks, so the latter is a good number for the number of rows.
        cusp_paths = np.zeros((max_num_switches, max_num_branches),
                              dtype=object)

        cusp_end_half_branches = np.zeros(max_num_switches, dytpe=np.int)
        # branch_to_cusp = np.zeros((2, max_num_branches), dtype=np.int)
        # count = 0
        # for b in tt.branches():
        #     for sgn in [-1, 1]:
        #         br = sgn*b
        #         idx = 0 if sgn == 1 else 1
        #         sw = tt.branch_endpoint(-br)
        #         if tt.outgoing_branch(sw, 0, RIGHT) != br:
        #             branch_to_cusp[idx, b-1] = count
        #             count += 1

        switch_pos_to_cusp_idx = np.zeros(train_track._outgoing_branches.shape,
                                          dtype=np.int)
        count = 0
        for sw in tt.switches():
            for sgn in [-1, 1]:
                or_sw = sgn * sw
                idx = 0 if sgn == 1 else 1
                for pos in range(tt.num_outgoing_branches(or_sw)-1):
                    switch_pos_to_cusp_idx[idx, sw-1, pos] = count
                    count += 1

        return cls(train_track, train_track.copy(),
                   train_paths,
                   half_branch_map,
                   hb_between_branches,
                   branch_to_cusp_idx)

    def delete_branch_from_small(self, branch):
        """Update the carrying data if a branch is deleted or contracted to a
        point.
        """
        br = abs(branch)
        self._train_paths[br-1].fill(0)
        self._half_branch_map[to_index(br)] = 0
        self._half_branch_map[to_index(-br)] = 0
        self._hb_between_branches[to_index(br)].fill(0)
        self._hb_between_branches[to_index(-br)].fill(0)

        # The only real update is for self._cusp_paths. Two cusps are going
        # away, so we need to delete the cusp paths, and the corresponding
        # branch-to-cusp pointers.
        assert(self._small_tt.is_trivalent())
        assert(self._small_tt.branch_type(branch) == SMALL_COLLAPSIBLE)

        sw = self._small_tt.branch_endpoint(branch)
        if self._small_tt.outgoing_branch(sw, 0) == -branch:
            # In this case, the branch is left-turning (the train has to turn
            # left in order to turn onto the branch, no matter which side it is
            # coming from).

            # In this case, the two cusps that are deleted are indexed by
            # +/-branch.
            for side in range(2):
                cusp_idx = self._branch_to_cusp[side, abs(branch)-1]
                self._cusp_paths[cusp_idx].fill(0)
                self._branch_to_cusp[side, abs(branch)-1] = 0
        else:
            # In this case, the branch is right-turning, so the two deleted
            # cusps are indexed by

            # TODO: Revise the implementation of cusp paths later.
            pass

    def trim(self, trim_from_idx, trimmed_path_idx):
        """Update the carrying data when a train path is trimmed off of
        another.

        self._half_branch_map is not updated and self._hb_between_branches is
        only half-way updated.
        """
        self._train_paths[abs(trim_from_idx)-1] -= \
            self._train_paths[abs(trimmed_path_idx)-1]
        # self._half_branch_map is difficult to update. We have to do it
        # elsewhere.
        self._hb_between_branches[:, :, abs(trim_from_idx)-1] -= \
            self._hb_between_branches[:, :, abs(trimmed_path_idx)-1]

        # self._hb_between_branches[to_index(-trim_from_idx)] = ...
        # This is also difficult, since we don't know the half-branch map.

    def outgoing_cusp_path_indices_in_small_tt(self, switch):
        """Return the numbers of the cusp paths outgoing from a switch.
        """
        ls = []
        for i in range(self._small_tt.num_outgoing_branches()-1):
            br = self._small_tt.outgoing_branch(switch, i)
            ls.append(self._branch_to_cusp_idx[to_index(br)])
        return ls

    def outgoing_path_indices_in_small_tt(self, switch):
        """Return the numbers of all outgoing branches and cusp pahts from a
        switch. 
        """
        return self._small_tt.outgoing_branches(switch) +\
            self.outgoing_cusp_path_indices_in_small_tt(switch)

    def isotope_switch_as_far_as_possible(self, switch):
        """Isotopes a switch of the small train track in the positive direction
        as far as possible.
        """
        # TODO: rewrite this
        small_tt = self._small_tt

        outgoing_path_indices = \
            self.outgoing_path_indices_in_small_tt(switch)

        min_path_indices = self.shortest_paths(outgoing_path_indices)
        min_path = self._train_paths[abs(min_path_idx)-1]

        outgoing_path_indices_neg = \
            self.outgoing_path_indices_in_small_tt(-switch)
        
        for br in outgoing_path_indices_neg:
            if small_tt.is_branch(br):
                # make sure there is no branch that circles back
                assert(small_tt.branch_endpoint(br) != -switch)
            self.append(-br, min_path_idx)

        for br in outgoing_path_indices:
            # we trim everything other than the shortest path, because once the
            # shortest path is trimmed, it becomes the zero path, so that won't
            # be available for trimming.
            if br != min_path_idx:
                self.trim(-br, -min_path_idx)

        self.trim(-br, -br)  # TODO: or self.delete_branch_from_small(br)?

        # Next we fix the half-branch maps of the trimmed branches. For
        # simplicity, we only implement this when there are at most two
        # outgoing branches.
        if len(self.num_outgoing_branches(switch) > 2):
            raise NotImplementedError

        # if tt.num_outgoing_branches(switch) > 2: # if there are more outgoing
        # branches, then there are more than one # cusps, which means we would
        # have to find the minimum of the cusps # paths. raise
        # NotImplementedError

        # if tt.num_outgoing_branches(switch) == 1:
        #     # in this case there is no obstruction for the isotopy.
        #     for br in tt.outgoing_branches(-switch):
        #         assert(-br != branch)
        #         self.append(-br, branch)
        #     self.delete_branch_from_small(branch)

        if tt.num_outgoing_branches(switch) == 2:
            # we can push the switch as far as the cusp path allows it.
            if tt.outgoing_branch(switch, 0) == branch:
                isotopy_side = LEFT
            if tt.outgoing_branch(switch, 1) == branch:
                isotopy_side = RIGHT
            else:
                assert(False)

            cusp_path = self.cusp_path(switch, 0)
            b_left = small_tt.outgoing_branch(switch, 0)
            b_right = small_tt.outgoing_branch(switch, 1)
            branch_path_left = self.branch_path(b_left)
            branch_path_right = self.branch_path(b_right)

            # finding the shortest of the three paths. That's how far the
            # isotopy can go.
            paths = [branch_path_left, branch_path_right, cusp_path]
            idx = self.shortest_path(paths)
            sortest_path = paths[i]
            neg_branch = self.outgoing_branch(-switch, 0)

            self._train_paths[abs(b_left)-1] -= shortest_path
            self._train_paths[abs(b_right)-1] -= shortest_path
            self.cusp_path(switch, 0) -= shortest_path
            self._train_paths[abs(neg_branch)-1] += shortest_path

            end_hb = self.end_hb_of_cusp_path(switch, 0)
            self._half_branch_map[to_index(neg_branch)] = end_hb
            end_sw = small_tt.branch_endpoint(-end_hb)

            # the other two half-branches will be one of the two half-branches
            # off of -end_sw.
            # If there is only one branch on that side, then
            # there is no choice. If there are two, then it is less obvious
            # which way b_left and b_right goes into. This can be computed from
            # the position of the end of the cusp path between the branches.
            if self.is_smaller(cusp_path, branch_path_left) and \
               self.is_smaller(cusp_path, branch_path_right):
                # In this case the cusp_path is the unique shortest path, so
                # the isotopy goes all the way to the cusp of the large train
                # track. So the values of the new half-branch maps are the two
                # half-branches next to that cusp of the large branch.
            self._half_branch_map[to_index(b_left)]

            if isotopy_side == LEFT and cusp_path == branch_path_left or\
               isotopy_side == RIGHT and cusp_path == branch_path_right:
                pass

    def shortest_paths(indices):
        """Return the shortest paths of the paths provided.

        If there is no shortest path (this is possible, since paths are arrays
        of integers, so the relation is a partial order, not an order), then it
        returns an error. But in our applications, this should not happen.

        OUTPUT:

        the list of indices of the shortest paths

        """
        for i in range(len(indices)):
            path = self._train_paths[abs(indices[i])-1]
            if all(is_smaller_or_equal(path,
                                       self._train_paths[abs(j)-1])
                   for j in indices):
                break
        else:
            raise ValueError("There is no shortest path!")

        ls = [indices(i)]
        for k in range(i+1, len(indices)):
            if is_equal(path, self._train_paths[abs(indices[k])-1]):
                ls.append(indices[k])
        return ls

    def branch_path(self, branch):
        """Return the train path of the specified branch.
        """
        return self._train_paths[abs(branch)-1]

    def cusp_path(self, switch, pos):
        """Return the path corresponding to the cusp at the specified cusp and
        position.
        """
        idx = self._switch_pos_to_cusp_idx[to_index(switch)][pos]
        return self._cusp_paths[idx]

    def end_hb_of_cusp_path(self, switch, pos):
        """Return the ending half-branch of the cusp path at the specified
        switch and position.
        """
        idx = self._switch_pos_to_cusp_idx[to_index(switch)][pos]
        return self._cusp_end_half_branches[idx]

    def small_tt(self):
        return self._small_tt

    def large_tt(self):
        return self._large_tt

    def __mul__(self):
        """
        Compose two carrying maps if possible.
        """
        pass

    def compute_measure_on_codomain(self):
        """
        Compute the measure on the codomain from the measure of the domain.
        """
        pass

    def unzip_codomain(self, branch):
        """Unzips the codomain and, if necessary, the domain, too.

        The domain has to be a measured train track. If there is a way
        to unzip the codomain so that the domain is carried, then that
        unzipping is performed and the domain does not change. In this
        case, the measure on the domain does not play a role. If there
        is no way to split the codomain so that the domain is carried,
        then the domain is unzipped according to the measure, and the
        codomain is unzipped accordingly to preserve the carrying
        relationship. If there are multiple way to unzip the domain
        according to the measure, then one of the possible unzips is
        performed - it is not specified which one.

        Nothing is returned, all components of the carrying map are
        changed internally.

        INPUT:

        - ``branch`` --

        """
        pass

    # ------------------------------------------------------------
    # Teichmuller/Alexander polynomial computation.

    def action_on_cohomology(self):
        pass

    def invariant_cohomology(self):
        pass

    def teichmuller_polynomial(self):
        pass
