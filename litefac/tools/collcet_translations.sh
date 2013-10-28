#! /bin/bash

po1=`python -c "from flask.ext import databrowser; print databrowser.__path__[0]"`"/translations/zh_CN/LC_MESSAGES/messages.po"
po2=`python -c "from flask.ext import report; print report.__path__[0]"`"/translations/zh_CN/LC_MESSAGES/messages.po"
msgcat $po1 $po2 | sed '/fuzzy/d' > translations/zh_CN/LC_MESSAGES/messages.po
pybabel compile -d translations
