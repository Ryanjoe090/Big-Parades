import requests
import argparse
from bs4 import BeautifulSoup, Tag
from datetime import datetime
import multiprocessing

#Kinda depends how the indexer puts the parade in. May not work. Humans...
def strip_band_name(band_name):
	new_band_name = band_name.strip(' ')
	new_band_name = new_band_name.strip('*')
	new_band_name = new_band_name.strip('#')
	new_band_name = new_band_name.strip('*')
	new_band_name = new_band_name.strip('#')
	return new_band_name

def parse_upcoming_parade(tag):
	data = tag.find_all('td')
	date = datetime.strptime(data[0].text, '%d/%m/%Y')
	parade = strip_band_name(data[1].text)
	id = data[1].find('a')['href'].split('=')[1]
	town = data[2].text
	start_time = data[3].text
	determination = data[4].text
	meta_dict = {'date': date, 'parade': parade, 'id': id, 'town': town, 'time': start_time, 'determination': determination}
	return meta_dict

def get_meta_entries():
	home_page = requests.get("https://www.paradescommission.org/Home.aspx")
	meta_entries = []
	if home_page.status_code == 200:
		content = home_page.content
		soup = BeautifulSoup(content, 'html.parser')
		table = soup.find_all('table', {'class': 'HomePageTable'})
		upcoming_parades = [x for x in table[0] if isinstance(x, Tag)]
		for tag in upcoming_parades[1:]:
			parsed_entry = parse_upcoming_parade(tag)
			meta_entries.append(parsed_entry)
	return meta_entries

def quick_multi(function, list):
	NUM_WORKERS = 24
	pool = multiprocessing.Pool(processes=NUM_WORKERS)
	results = pool.map_async(function, list)
	# results.wait()
	pool.close()
	pool.join()
	return results.get()

def parse_route(route_tag):
	route = str(route_tag)
	route = route[4:][:len(route)-9].split('<br/>')
	return route

def parse_further_info_table(further_information):
	outward_start_time = '12:00' #defaults in case there is human error in table
	outward_end_time = '12:00' #Will keep it string for meantime
	outwards_route = []
	number_of_bands = 0
	bands = []
	participants = 0
	supporters = 0

	for tag in further_information: #Going to just use if/else in case table order changes
		if tag.find('th').text == 'Start Time of Outward Route':
			outward_start_time = tag.find('td').text
		elif tag.find('th').text == 'Proposed Outward Route':
			route = tag.find('td')
			outwards_route = parse_route(route) #make a function to parse
		elif tag.find('th').text == 'End Time of Outward Route':
			outward_end_time = tag.find('td').text
		elif tag.find('th').text == 'Number of Bands':
			try:
				number_of_bands = int(tag.find('td').text)
			except: #is a string. try format x-y
				try:
					number_of_bands = int(tag.find('td').text.split('-')[0])
				except: #probs some boyo talking about tractors again
					try:
						number_of_bands = int(tag.find('td').text.split(' ')[0])
					except: #I give up. Why the commission has unsanitised data input i dont know. Try putting XSS as your bands
						pass
		elif tag.find('th').text == 'Bands':
			bands = [x.strip() for x in tag.find('td').text.split(',')] #Possibly make function to parse
		elif tag.find('th').text == 'Expected Number of Participants':
			try:
				participants = int(tag.find('td').text)
			except:
				pass #probably no number filled in or unknown
		elif tag.find('th').text == 'Expected Number of Supporters':
			try:
				supporters = int(tag.find('td').text)
			except:
				pass #probably no number filled in or unknown
	return {'outward_start_time': outward_start_time, 'outward_end_time': outward_end_time, 'outward_route': outwards_route, 'number_of_bands': number_of_bands, 'bands': bands, 'participants': participants, 'supporters': supporters}


def fetch_parade_data(entry):
	buffer_entry = entry.copy()
	url = f'https://www.paradescommission.org/viewparade.aspx?id={buffer_entry["id"]}'
	parade_response = requests.get(url)
	if parade_response.status_code == 200:
		content = parade_response.content
		soup = BeautifulSoup(content, 'html.parser')
		main_content = soup.find('div', {'class': 'o-main-content'})
		table = main_content.find_all('table', {'class': 'HomePageTable'})
		header = [x for x in table[0] if isinstance(x, Tag)]
		further_information = [x for x in table[1] if isinstance(x, Tag)]
		reference_number = header[1].find_all('td')[0].text
		buffer_entry['parade'] = strip_band_name(header[1].find_all('td')[1].text)
		buffer_entry['reference'] = reference_number
		further_information_parsed = parse_further_info_table(further_information)
		buffer_entry.update(further_information_parsed)
	return buffer_entry

def get_all_data(meta_data):
	enriched_entries = quick_multi(fetch_parade_data, meta_data)
	return enriched_entries

def get_top_ten(meta_data):
	data = get_all_data(meta_data)
	processed_data = process_top_ten(data)
	for parade in processed_data:
		pretty_print_parade(parade)

def pretty_print_parade(parade):
	print(parade['parade'])
	print('Date: ' + str(parade['date']))
	print('Town: ' + parade['town'])
	print('Route: ' + ','.join(parade['outward_route']))
	print('Reference: ' + parade['reference'])
	print('Number of Bands: ' + str(parade['number_of_bands']))
	print('Bands: ' + ','.join(parade['bands']))
	print('Participants: ' + str(parade['participants']))
	print('https://www.paradescommission.org/viewparade.aspx?id=' + str(parade['id']))
	print('\n')

def process_top_ten(data):
	buffer_list = sorted(data, key=lambda k: k['number_of_bands'])
	buffer_list.reverse()
	filtered_buffer = [x for x in buffer_list if len(x['bands']) > 1][:10] #This can go any way really. I can change. This is to filter out the boyos on their 200 tractors
	return filtered_buffer

def band_fuzzy_search(parade, band):
	band_lwr = band.lower()
	for participating_band in parade['bands']:
		if band_lwr in participating_band.lower():
			return True
	return False

def road_fuzzy_search(parade, road):
	road_lwr = road.lower()
	for outward_road in parade['outward_route']:
		if road_lwr in outward_road.lower():
			return True
	return False

def band_filter_process(data, band):
	band_parades = [x for x in data if band_fuzzy_search(x, band)]
	return band_parades

def road_filter_process(data, band):
	road_parades = [x for x in data if road_fuzzy_search(x, band)]
	return road_parades

def filter_by_band(meta_data, band):
	data = get_all_data(meta_data)
	processed_data = band_filter_process(data, band)
	for parade in processed_data:
		pretty_print_parade(parade)

def filter_by_road(meta_data, road):
	data = get_all_data(meta_data)
	processed_data = road_filter_process(data, road)
	for parade in processed_data:
		pretty_print_parade(parade)

def main(args):
	meta_data = get_meta_entries()
	if args['top'] == True:
		get_top_ten(meta_data)
	elif args['band']:
		filter_by_band(meta_data, args['band'])
	elif args['road']:
		filter_by_road(meta_data, args['road'])



if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Hello. Scrape Parades off the Commission Website.')
	parser.add_argument('-t', '--top', help='Top 10 Parades by Size', required=False, action="store_true")
	parser.add_argument('-b', '--band', help='List Parades involving Band. In quotes plz. It will be a contains search (~). Go nuts', type=str, required=False)
	parser.add_argument('-r', '--road', help='List Parades involving a Road. In quotes plz. It will be a contains search (~). Go nuts. Only matches on outward. Inputs are so unsanitised on the commission website.', type=str, required=False)
	args = vars(parser.parse_args())

	main(args)
