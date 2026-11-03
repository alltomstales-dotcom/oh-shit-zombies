"""Where a survivor can begin on the public server: named city centres, nobody's home street.

These are busy commercial districts, picked so that choosing one says nothing about a player. Their
map data is fetched once and cached, and they keep players close enough to share a world.
"""
STARTS = (
    {"id": "chicago", "label": "Chicago", "blurb": "The Loop, among the towers", "lat": 41.8807, "lng": -87.6278},
    {"id": "minneapolis", "label": "Minneapolis", "blurb": "Downtown, around Nicollet", "lat": 44.9778, "lng": -93.2650},
    {"id": "manchester", "label": "Manchester", "blurb": "The city centre, and six hours ahead of Chicago's daylight", "lat": 53.4794, "lng": -2.2400},
)


def by_id(start_id):
    return next((s for s in STARTS if s["id"] == start_id), None)


def catalog():
    return [{"id": s["id"], "label": s["label"], "blurb": s["blurb"]} for s in STARTS]
