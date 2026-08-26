# Gunicorn settings used by Posit Connect. The default 30s worker timeout is too
# short for the first request, which resolves the site id and pulls four
# SharePoint lists over Graph.
timeout = 300
graceful_timeout = 30
workers = 2          # each worker keeps its own in-process cache; 2 is plenty
