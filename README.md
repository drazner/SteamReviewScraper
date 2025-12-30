# SteamReviewScraper
This is a Python tool I created which downloads Steam Store reviews for a single game based on AppID using the Steam API. The tool normalizes the extracted dataset and saves it to JSON format for downstream data analysis with Pandas or Juptyer Notebook.

# How to run Python Scraper tool 
All you need to do is download the SteamReviewScraper.py file and run it. 
If you run the program by default, it will extract the first 1,000 reviews from the Steam game Pixelate TD with appid = 4134990. A default call would look like this:


`python3 SteamReviewScraper.py`



You can learn more about a number of parameters available that are detailed here: 


`python3 SteamReviewScraper.py --help`



Here is an example of a custom run where you download the first 200 English reviews for Elden Ring (appid = 1245620) and save it to a file called EldenRingEnglish.json 


`python3 SteamReviewScraper.py --appid 1245620 --language "english" --max-reviews 200 --out EldenRingEnglish.json`

The results are stored in the same directory under a filename that is defaultly formatted like so: "steam_reviews_{appid}.json"



# Data Analysis on sample game (first 100,000 reviews of Stardew Valley) 
I used my scraper to download 100,000 reviews from the Steam game Stardew Valley into a normalized JSON format. 

I then conducted some rudimentary data analysis using Pandas to generate a few quick insights about how different pieces of data relate to the review.

## Insights

### Here are some averages for all of the boolean columns in the dataset
<img width="501" height="200" alt="image" src="https://github.com/user-attachments/assets/24231918-b910-441b-b902-b46ae32c290a" />



### Here is a visual displaying the relation between how long the reviewer played the game and their rating of the game

<img width="531" height="461" alt="image" src="https://github.com/user-attachments/assets/67424b1f-866d-4927-833a-24169e826075" />


### Here is a visual displaying how the length of the review (in characters) impacted the rating of the game

<img width="550" height="468" alt="image" src="https://github.com/user-attachments/assets/273d9f64-0aa7-4ace-9277-c7f3e061f4ed" />


### Here is a query displaying how the reviewer's language impacted the reviewer's rating of the game

<img width="253" height="484" alt="image" src="https://github.com/user-attachments/assets/9c06a3a7-ffed-4b25-b44c-25b2d3392dae" />
