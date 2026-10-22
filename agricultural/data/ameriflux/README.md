AmeriFlux daily files for the Mead, Nebraska sites (CC-BY-4.0). Do not commit the raw zips (hundreds of MB). Reduce each zip on your own computer. No Python needed: double-click `agricultural/prototypes/tools/ameriflux_daily.html`, drop the zip on the page, and save the CSV it offers (runs entirely in the browser). With Python instead:

    python3 agricultural/prototypes/tools/ameriflux_daily.py AMF_US-Ne3_BASE_*.zip

and commit the resulting `US-Ne3_daily.csv` (a few hundred KB) here. Cite the site DOIs when publishing: US-Ne1 10.17190/AMF/1246084, US-Ne2 10.17190/AMF/1246085, US-Ne3 10.17190/AMF/1246086, and acknowledge AmeriFlux.
