/**
 * Twitter/X Scraper using Apify
 * Uses Apify's maintained Twitter scraper actor
 * FREE TIER: 30 seconds/day compute time (~100 tweets/day)
 * 
 * Setup:
 * 1. Create free account at apify.com
 * 2. Get API token from Settings -> Integrations
 * 3. Set APIFY_TOKEN environment variable or edit this file
 * 
 * Built by Friday for skripsi project
 */

import * as fs from 'fs';
import * as https from 'https';

// Set your Apify token here or via APIFY_TOKEN env variable
const APIFY_TOKEN = process.env.APIFY_TOKEN || 'YOUR_APIFY_TOKEN_HERE';

// Apify Twitter Scraper Actor ID
const ACTOR_ID = 'apidojo/tweet-scraper';

/**
 * Run Apify actor
 */
async function runApifyActor(input) {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify(input);

        const options = {
            hostname: 'api.apify.com',
            path: `/v2/acts/${ACTOR_ID}/run-sync-get-dataset-items?token=${APIFY_TOKEN}`,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': data.length
            },
            timeout: 120000 // 2 minutes
        };

        const req = https.request(options, (res) => {
            let body = '';
            res.on('data', chunk => body += chunk);
            res.on('end', () => {
                try {
                    resolve({
                        status: res.statusCode,
                        data: JSON.parse(body)
                    });
                } catch (e) {
                    resolve({
                        status: res.statusCode,
                        data: body
                    });
                }
            });
        });

        req.on('error', reject);
        req.on('timeout', () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });

        req.write(data);
        req.end();
    });
}

/**
 * Search tweets
 */
async function searchTweets(keyword, count = 100) {
    console.log(`🔍 Searching for: "${keyword}"`);
    console.log(`   Target: ${count} tweets`);
    console.log(`   Note: Free tier allows ~100 tweets/day\n`);

    try {
        const input = {
            searchTerms: [keyword],
            maxTweets: count,
            addUserInfo: true,
            scrapeTweetReplies: false,
        };

        console.log('⏳ Running Apify actor (this may take 1-2 minutes)...');

        const response = await runApifyActor(input);

        if (response.status !== 201 && response.status !== 200) {
            if (response.status === 401) {
                console.log('\n❌ Error: Invalid Apify token');
                console.log('   Get your free token at: https://console.apify.com/account/integrations');
                return [];
            }
            console.log(`\n❌ API Error: ${response.status}`);
            console.log(response.data);
            return [];
        }

        const tweets = (response.data || []).map(item => ({
            id: item.id,
            text: item.text || item.full_text,
            created_at: item.created_at,
            language: item.lang,

            like_count: item.favorite_count || item.public_metrics?.like_count || 0,
            retweet_count: item.retweet_count || item.public_metrics?.retweet_count || 0,
            reply_count: item.reply_count || item.public_metrics?.reply_count || 0,

            user: {
                id: item.author_id || item.user?.id_str,
                username: item.author?.username || item.user?.screen_name,
                display_name: item.author?.name || item.user?.name,
                followers_count: item.author?.followersCount || item.user?.followers_count || 0,
            },

            hashtags: item.entities?.hashtags?.map(h => h.tag || h.text) || [],
        }));

        console.log(`\n✅ Fetched ${tweets.length} tweets`);
        return tweets;

    } catch (error) {
        console.error(`\n❌ Error: ${error.message}`);
        return [];
    }
}

/**
 * Export functions
 */
function exportJSON(tweets, filename) {
    fs.writeFileSync(filename, JSON.stringify(tweets, null, 2), 'utf-8');
    console.log(`📁 Exported to ${filename}`);
}

function exportCSV(tweets, filename) {
    if (tweets.length === 0) return;

    const headers = ['id', 'text', 'created_at', 'language', 'like_count', 'retweet_count', 'username', 'hashtags'];
    const rows = tweets.map(t => [
        t.id,
        `"${(t.text || '').replace(/"/g, '""').replace(/\n/g, ' ')}"`,
        t.created_at,
        t.language,
        t.like_count,
        t.retweet_count,
        t.user?.username,
        `"${(t.hashtags || []).join(',')}"`
    ].join(','));

    fs.writeFileSync(filename, [headers.join(','), ...rows].join('\n'), 'utf-8');
    console.log(`📁 Exported to ${filename}`);
}

function printSummary(tweets) {
    if (tweets.length === 0) {
        console.log('\n⚠️ No tweets found');
        return;
    }

    console.log('\n📊 Summary:');
    console.log(`   Total tweets: ${tweets.length}`);

    const langs = {};
    tweets.forEach(t => {
        const lang = t.language || 'unknown';
        langs[lang] = (langs[lang] || 0) + 1;
    });

    console.log('   Languages:');
    Object.entries(langs)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .forEach(([lang, count]) => console.log(`     - ${lang}: ${count}`));

    const totalLikes = tweets.reduce((sum, t) => sum + (t.like_count || 0), 0);
    console.log(`   Total Likes: ${totalLikes.toLocaleString()}`);
}

// Main
async function main() {
    const args = process.argv.slice(2);
    let keyword = null;
    let count = 50;
    let outputCsv = null;

    for (let i = 0; i < args.length; i++) {
        switch (args[i]) {
            case '-k':
            case '--keyword':
                keyword = args[++i];
                break;
            case '-c':
            case '--count':
                count = parseInt(args[++i]) || 50;
                break;
            case '--csv':
                outputCsv = args[++i];
                break;
            case '-h':
            case '--help':
                showHelp();
                return;
        }
    }

    if (APIFY_TOKEN === 'YOUR_APIFY_TOKEN_HERE') {
        console.log('⚠️ Apify token not set!\n');
        console.log('Setup (free):');
        console.log('1. Create account at https://apify.com (free)');
        console.log('2. Go to Settings -> Integrations');
        console.log('3. Copy your API token');
        console.log('4. Run: set APIFY_TOKEN=your_token_here');
        console.log('   Or edit scraper_apify.js and set the token there\n');
        return;
    }

    if (!keyword) {
        showHelp();
        return;
    }

    console.log('🐦 Twitter/X Scraper (Apify)\n');

    const tweets = await searchTweets(keyword, count);
    printSummary(tweets);

    if (tweets.length > 0) {
        const filename = `tweets_${keyword.replace(/\s+/g, '_').substring(0, 20)}`;
        exportJSON(tweets, `${filename}.json`);

        if (outputCsv) {
            exportCSV(tweets, outputCsv);
        }
    }

    console.log('\n✨ Done!');
}

function showHelp() {
    console.log(`
🐦 Twitter/X Scraper (Apify)

FREE tier: 30 seconds compute/day (~100 tweets)
Paid: Unlimited (starts at $5/month)

Setup:
    1. Create free account at https://apify.com
    2. Get API token from Settings -> Integrations
    3. Set token: set APIFY_TOKEN=your_token

Usage:
    node scraper_apify.js -k <keyword> [-c count] [--csv file]

Examples:
    node scraper_apify.js -k "jokowi" -c 50
    node scraper_apify.js -k "indonesia" -c 100 --csv hasil.csv
`);
}

main().catch(console.error);
