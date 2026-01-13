/**
 * Twitter/X Scraper using rettiwt-api
 * 
 * IMPORTANT: Requires Twitter account for search functionality
 * Guest mode only works for: user profile details, user timelines
 * 
 * Built by Friday for skripsi project
 */

import { Rettiwt } from 'rettiwt-api';
import * as fs from 'fs';
import * as readline from 'readline';

// API Key storage file
const API_KEY_FILE = '.twitter_api_key';

/**
 * Load saved API key
 */
function loadApiKey() {
    try {
        if (fs.existsSync(API_KEY_FILE)) {
            return fs.readFileSync(API_KEY_FILE, 'utf-8').trim();
        }
    } catch (e) { }
    return null;
}

/**
 * Save API key
 */
function saveApiKey(apiKey) {
    fs.writeFileSync(API_KEY_FILE, apiKey, 'utf-8');
    console.log('✅ API Key saved!');
}

/**
 * Interactive prompt
 */
function question(prompt) {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });
    return new Promise(resolve => {
        rl.question(prompt, answer => {
            rl.close();
            resolve(answer);
        });
    });
}

/**
 * Parse tweet object to clean format
 */
function parseTweet(tweet) {
    return {
        id: tweet.id,
        text: tweet.fullText,
        created_at: tweet.createdAt,
        language: tweet.lang,

        // Engagement
        like_count: tweet.likeCount || 0,
        retweet_count: tweet.retweetCount || 0,
        reply_count: tweet.replyCount || 0,
        view_count: tweet.viewCount || 0,

        // User info
        user: {
            id: tweet.tweetBy?.id,
            username: tweet.tweetBy?.userName,
            display_name: tweet.tweetBy?.fullName,
            followers_count: tweet.tweetBy?.followersCount || 0,
            verified: tweet.tweetBy?.isVerified || false,
        },

        // Media & entities
        has_media: (tweet.media?.length || 0) > 0,
        hashtags: tweet.entities?.hashtags || [],
        mentions: tweet.entities?.mentionedUsers?.map(u => u.userName) || [],
        urls: tweet.entities?.urls?.map(u => u.expandedUrl) || [],
    };
}

/**
 * Search tweets by keyword
 */
async function searchTweets(rettiwt, keyword, count = 100) {
    console.log(`🔍 Searching for: "${keyword}"`);
    console.log(`   Target: ${count} tweets\n`);

    const tweets = [];
    let cursor = null;

    try {
        while (tweets.length < count) {
            // Search tweets
            const result = await rettiwt.tweet.search({
                rawQuery: keyword,
                count: Math.min(20, count - tweets.length),
                cursor: cursor,
            });

            if (!result || !result.list || result.list.length === 0) {
                console.log('   No more tweets available');
                break;
            }

            // Parse and add tweets
            for (const tweet of result.list) {
                if (tweets.length >= count) break;
                tweets.push(parseTweet(tweet));

                // Progress indicator
                if (tweets.length % 10 === 0) {
                    process.stdout.write(`   Progress: ${tweets.length}/${count}\r`);
                }
            }

            // Get next cursor for pagination
            cursor = result.next?.value;
            if (!cursor) break;

            // Small delay to avoid rate limiting
            await sleep(500);
        }

        console.log(`\n✅ Fetched ${tweets.length} tweets`);
        return tweets;

    } catch (error) {
        console.error(`\n❌ Error: ${error.message}`);
        if (error.message.includes('401') || error.message.includes('403')) {
            console.log('\n💡 Hint: Your API key may have expired. Run with --setup to re-authenticate.');
        }
        if (tweets.length > 0) {
            console.log(`   Returning ${tweets.length} tweets collected so far`);
        }
        return tweets;
    }
}

/**
 * Export tweets to JSON file
 */
function exportJSON(tweets, filename) {
    fs.writeFileSync(filename, JSON.stringify(tweets, null, 2), 'utf-8');
    console.log(`📁 Exported to ${filename}`);
}

/**
 * Export tweets to CSV file
 */
function exportCSV(tweets, filename) {
    if (tweets.length === 0) {
        console.log('⚠️ No tweets to export');
        return;
    }

    const headers = [
        'id', 'text', 'created_at', 'language',
        'like_count', 'retweet_count', 'reply_count', 'view_count',
        'user_id', 'username', 'display_name', 'followers_count',
        'hashtags', 'mentions'
    ];

    const rows = tweets.map(t => [
        t.id,
        `"${(t.text || '').replace(/"/g, '""').replace(/\n/g, ' ')}"`,
        t.created_at,
        t.language,
        t.like_count,
        t.retweet_count,
        t.reply_count,
        t.view_count,
        t.user?.id,
        t.user?.username,
        `"${t.user?.display_name || ''}"`,
        t.user?.followers_count,
        `"${(t.hashtags || []).join(',')}"`,
        `"${(t.mentions || []).join(',')}"`
    ].join(','));

    const csv = [headers.join(','), ...rows].join('\n');
    fs.writeFileSync(filename, csv, 'utf-8');
    console.log(`📁 Exported to ${filename}`);
}

/**
 * Print summary of scraped tweets
 */
function printSummary(tweets) {
    if (tweets.length === 0) {
        console.log('\n⚠️ No tweets found');
        return;
    }

    console.log('\n📊 Summary:');
    console.log(`   Total tweets: ${tweets.length}`);

    // Language distribution
    const langs = {};
    tweets.forEach(t => {
        const lang = t.language || 'unknown';
        langs[lang] = (langs[lang] || 0) + 1;
    });
    console.log('   Languages:');
    Object.entries(langs)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .forEach(([lang, count]) => console.log(`     - ${lang}: ${count}`));

    // Engagement
    const totalLikes = tweets.reduce((sum, t) => sum + (t.like_count || 0), 0);
    const totalRetweets = tweets.reduce((sum, t) => sum + (t.retweet_count || 0), 0);
    console.log(`   Total Likes: ${totalLikes.toLocaleString()}`);
    console.log(`   Total Retweets: ${totalRetweets.toLocaleString()}`);

    // Top tweet
    if (tweets.length > 0) {
        const topTweet = tweets.reduce((max, t) =>
            (t.like_count + t.retweet_count) > (max.like_count + max.retweet_count) ? t : max
        );
        console.log(`\n   🔥 Top Tweet by @${topTweet.user?.username}:`);
        console.log(`      "${topTweet.text?.substring(0, 80)}..."`);
        console.log(`      ❤️ ${topTweet.like_count} | 🔄 ${topTweet.retweet_count}`);
    }
}

/**
 * Setup API Key from cookies
 */
async function setupApiKey() {
    console.log('\n🔧 Setup API Key\n');
    console.log('Untuk scraping, Anda perlu API key dari akun Twitter.');
    console.log('Ikuti langkah berikut:\n');
    console.log('1. Buka Twitter/X di browser dan login ke akun Anda');
    console.log('2. Tekan F12 untuk buka Developer Tools');
    console.log('3. Pergi ke tab "Application" (Chrome) atau "Storage" (Firefox)');
    console.log('4. Di sidebar, pilih "Cookies" → "https://twitter.com" atau "https://x.com"');
    console.log('5. Cari cookies: auth_token, ct0');
    console.log('6. Copy nilai kedua cookies tersebut\n');

    const authToken = await question('Masukkan auth_token: ');
    const ct0 = await question('Masukkan ct0: ');

    if (!authToken || !ct0) {
        console.log('❌ Kedua nilai harus diisi!');
        return null;
    }

    // Encode to API key format
    const apiKey = Buffer.from(JSON.stringify({
        auth_token: authToken,
        ct0: ct0,
    })).toString('base64');

    // Test the API key
    console.log('\n🔄 Testing API key...');
    try {
        const rettiwt = new Rettiwt({ apiKey });
        await rettiwt.user.details('twitter');
        console.log('✅ API key valid!');
        saveApiKey(apiKey);
        return apiKey;
    } catch (error) {
        console.log('❌ API key invalid! Pastikan cookies benar.');
        return null;
    }
}

/**
 * Sleep helper
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Main function - CLI interface
 */
async function main() {
    const args = process.argv.slice(2);

    // Parse arguments
    let keyword = null;
    let count = 100;
    let outputJson = null;
    let outputCsv = null;
    let doSetup = false;

    for (let i = 0; i < args.length; i++) {
        switch (args[i]) {
            case '-k':
            case '--keyword':
                keyword = args[++i];
                break;
            case '-c':
            case '--count':
                count = parseInt(args[++i]) || 100;
                break;
            case '-o':
            case '--output':
                outputJson = args[++i];
                break;
            case '--csv':
                outputCsv = args[++i];
                break;
            case '--setup':
                doSetup = true;
                break;
            case '-h':
            case '--help':
                showHelp();
                return;
        }
    }

    console.log('🐦 Twitter/X Scraper\n');

    // Handle setup
    if (doSetup) {
        await setupApiKey();
        return;
    }

    // Check for API key
    let apiKey = loadApiKey();
    if (!apiKey) {
        console.log('⚠️ API key not found. Please run setup first:\n');
        console.log('   node scraper.js --setup\n');
        return;
    }

    if (!keyword) {
        console.log('❌ Error: Keyword is required');
        showHelp();
        return;
    }

    // Create authenticated client
    console.log('🔑 Using saved API key...\n');
    const rettiwt = new Rettiwt({ apiKey });

    // Scrape tweets
    const tweets = await searchTweets(rettiwt, keyword, count);

    // Print summary
    printSummary(tweets);

    // Export
    if (tweets.length > 0) {
        const defaultFilename = `tweets_${keyword.replace(/\s+/g, '_').substring(0, 20)}`;
        exportJSON(tweets, outputJson || `${defaultFilename}.json`);

        if (outputCsv) {
            exportCSV(tweets, outputCsv);
        }
    }

    console.log('\n✨ Done!');
}

function showHelp() {
    console.log(`
🐦 Twitter/X Scraper

PENTING: Scraper ini memerlukan akun Twitter untuk search.
         Jalankan --setup dulu untuk konfigurasi.

Usage:
    node scraper.js --setup              # Setup API key (pertama kali)
    node scraper.js -k <keyword>         # Scrape tweets

Options:
    -k, --keyword <text>   Search keyword (required)
    -c, --count <number>   Number of tweets (default: 100)  
    -o, --output <file>    Output JSON file
    --csv <file>           Also export to CSV
    --setup                Setup API key dari browser cookies

Examples:
    node scraper.js --setup
    node scraper.js -k "jokowi" -c 100
    node scraper.js -k "pilpres 2024" -c 500 --csv hasil.csv
`);
}

// Run main
main().catch(console.error);
