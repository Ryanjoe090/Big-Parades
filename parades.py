import requests
import re
import sys
from datetime import datetime

#Get List of Parade IDs (viewparade.aspx?id=<ID HERE>)
home_page = requests.get("https://www.paradescommission.org/Home.aspx")
home_temp = re.sub(r'\s+', '', home_page.content)
table = re.search('(?<=<tableclass=\"HomePageTable\">)(.*)(?=</table>)',home_temp).group(0)
table = re.search('(?<=<tableclass=\"HomePageTable\">)(.*)(?=</table>)',table).group(0)
array = re.findall('(?<=<ahref=[\']\/viewparade\.aspx\?id\=)(.*?)(?=[\'])', table)

for item in array: #Find parade details. If it excepts. It probably means no bands. Im happy just to pass
	try:
		r = requests.get("https://www.paradescommission.org/viewparade.aspx?id=" + str(item))
		temp = re.sub(r'\s+', '', r.content)
		number_of_bands = re.search('(?<=<divclass=\"viewParadeInfoheader\">NumberofBands</div><divclass=\"viewParadeheaderinfoDetail\">)\d+',temp).group(0)
		date_of_parade = re.search('(?<=<divclass=\"viewParadeInfoheader\">DateofParade</div><divclass=\"viewParadeheaderinfoDetail\">)[\d\w]+', temp).group(0)
		detail_array = [x.lstrip().rstrip() for x in re.findall('(?<=<div class=\"viewParadeheaderDetail\">)([a-zA-Z\s\d\W]*?)(?=</div>)', r.content)]
		datetime_object = datetime.strptime(date_of_parade, '%d%B%Y')
		if int(number_of_bands) >= int(sys.argv[1]):
			if datetime_object > datetime.today():
				print "https://www.paradescommission.org/viewparade.aspx?id=" + str(item)
				print 'Parade ID: ' + str(detail_array[0])
				print 'Organisation: ' + str(detail_array[1])
				print 'Location: ' + str(detail_array[2])
				print 'Number of Bands: ' + str(number_of_bands)
				print datetime_object.strftime('%d, %b %Y')
	except Exception, e:
		pass
