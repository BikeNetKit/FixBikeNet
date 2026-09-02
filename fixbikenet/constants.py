"""Global constants for `fixbikenet` that can be tweaked during development, but 
should not be changed later by the user. Especially technical or internal 
constants start with an underscore.

_ROUTING_PENALTY : dict, default {0: 1.5, 1: 1}
    Factor to multiply length of non-pbi/pbi for routing, to avoid routing
    through parallel streets when slightly longer pbi is available. By 
    default, non-pbi counts as 50% longer than pbi.
_PROGRESS_BAR_LENGTH : int, default 23
    Character length of tqdm progress bars.
_PROGRESS_BAR_DESC_LENGTH : int, default 23
    Character length of tqdm progress bar descriptions. This is the space given 
    to text like "Importing network data ", which is at the maximum of 23 
    characters.
"""

_ROUTING_PENALTY = {0: 1.5, 1: 1}
_PROGRESS_BAR_LENGTH = 23
_PROGRESS_BAR_DESC_LENGTH = 24