/**
 * Twitter/X Scraper - Direct Cookie Authentication
 * Works with auth_token and ct0 cookies
 * 
 * Built by Friday for skripsi project
 */

import * as fs from 'fs';
import * as https from 'https';

// Twitter credentials
const AUTH_TOKEN = '598847410fe3cef2e7e8edc56d5ee4365ae7355a';
const CT0 = 'b72143b89ae2beb13c3b73af8e1a262bcf25ab0b2f7baf881e662a52bdda9cc19a87c322f77b26f59859a00b0316aa14823e1b6c9c87f0020be29f7da00fa22006696767bbfca73c30dc4fcbc0a17443';

// Twitter Bearer Token (public)
const BEARER_TOKEN = 'AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA';

/**
 * Make authenticated request to Twitter API
 */
async function twitterRequest(url, params = {}) {
    return new Promise((resolve, reject) => {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;

        const urlObj = new URL(fullUrl);

        const options = {
            hostname: urlObj.hostname,
            path: urlObj.pathname + urlObj.search,
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${BEARER_TOKEN}`,
                'Cookie': `auth_token=${AUTH_TOKEN}; ct0=${CT0}`,
                'X-Csrf-Token': CT0,
                'X-Twitter-Active-User': 'yes',
                'X-Twitter-Auth-Type': 'OAuth2Session',
                'X-Twitter-Client-Language': 'en',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Content-Type': 'application/json',
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve({
                        status: res.statusCode,
                        data: JSON.parse(data)
                    });
                } catch (e) {
                    resolve({
                        status: res.statusCode,
                        data: data
                    });
                }
            });
        });

        req.on('error', reject);
        req.end();
    });
}

/**
 * Search tweets using GraphQL API
 */
async function searchTweets(keyword, count = 100) {
    console.log(`🔍 Searching for: "${keyword}"`);
    console.log(`   Target: ${count} tweets\n`);

    const tweets = [];
    let cursor = null;

    // GraphQL query for search
    const features = {
        "rweb_tipjar_consumption_enabled": true,
        "responsive_web_graphql_exclude_directive_enabled": true,
        "verified_phone_label_enabled": false,
        "creator_subscriptions_tweet_preview_api_enabled": true,
        "responsive_web_graphql_timeline_navigation_enabled": true,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": false,
        "communities_web_enable_tweet_community_results_fetch": true,
        "c9s_tweet_anatomy_moderator_badge_enabled": true,
        "articles_preview_enabled": true,
        "tweetypie_unmention_optimization_enabled": true,
        "responsive_web_edit_tweet_api_enabled": true,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": true,
        "view_counts_everywhere_api_enabled": true,
        "longform_notetweets_consumption_enabled": true,
        "responsive_web_twitter_article_tweet_consumption_enabled": true,
        "tweet_awards_web_tipping_enabled": false,
        "creator_subscriptions_quote_tweet_preview_enabled": false,
        "freedom_of_speech_not_reach_fetch_enabled": true,
        "standardized_nudges_misinfo": true,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": true,
        "rweb_video_timestamps_enabled": true,
        "longform_notetweets_rich_text_read_enabled": true,
        "longform_notetweets_inline_media_enabled": true,
        "responsive_web_enhance_cards_enabled": false
    };

    try {
        while (tweets.length < count) {
            const variables = {
                rawQuery: keyword,
                count: 20,
                querySource: "typed_query",
                product: "Latest"
            };

            if (cursor) {
                variables.cursor = cursor;
            }

            const params = {
                variables: JSON.stringify(variables),
                features: JSON.stringify(features)
            };

            // Use SearchTimeline GraphQL endpoint
            const response = await twitterRequest(
                'https://x.com/i/api/graphql/MJpyQGqgklrVl_0X9gNy3A/SearchTimeline',
                params
            );

            if (response.status !== 200) {
                console.log(`   API Error: ${response.status}`);
                console.log(`   Response:`, JSON.stringify(response.data).substring(0, 200));
                break;
            }

            // Parse response
            const timeline = response.data?.data?.search_by_raw_query?.search_timeline?.timeline;
            if (!timeline) {
                console.log('   No timeline data');
                break;
            }

            const instructions = timeline.instructions || [];
            let entries = [];

            for (const instruction of instructions) {
                if (instruction.type === 'TimelineAddEntries') {
                    entries = instruction.entries || [];
                } else if (instruction.entries) {
                    entries = instruction.entries;
                }
            }

            if (entries.length === 0) {
                console.log('   No more tweets');
                break;
            }

            // Extract tweets from entries
            for (const entry of entries) {
                if (tweets.length >= count) break;

                const entryId = entry.entryId || '';

                // Skip cursor entries
                if (entryId.startsWith('cursor-')) {
                    if (entryId.includes('bottom')) {
                        cursor = entry.content?.value;
                    }
                    continue;
                }

                // Extract tweet data
                const tweetResult = entry.content?.itemContent?.tweet_results?.result;
                if (!tweetResult) continue;

                const tweet = extractTweet(tweetResult);
                if (tweet) {
                    tweets.push(tweet);
                    if (tweets.length % 10 === 0) {
                        process.stdout.write(`   Progress: ${tweets.length}/${count}\r`);
                    }
                }
            }

            // No cursor = no more pages
            if (!cursor) break;

            // Small delay
            await sleep(1000);
        }

        console.log(`\n✅ Fetched ${tweets.length} tweets`);
        return tweets;

    } catch (error) {
        console.error(`\n❌ Error: ${error.message}`);
        return tweets;
    }
}

/**
 * Extract tweet data from GraphQL result
 */
function extractTweet(result) {
    try {
        // Handle tweet with visibility or tombstone
        if (result.__typename === 'TweetWithVisibilityResults') {
            result = result.tweet;
        }

        if (!result || result.__typename === 'TweetTombstone') {
            return null;
        }

        const legacy = result.legacy || {};
        const user = result.core?.user_results?.result?.legacy || {};

        return {
            id: legacy.id_str || result.rest_id,
            text: legacy.full_text || '',
            created_at: legacy.created_at,
            language: legacy.lang,

            like_count: legacy.favorite_count || 0,
            retweet_count: legacy.retweet_count || 0,
            reply_count: legacy.reply_count || 0,
            quote_count: legacy.quote_count || 0,
            view_count: result.views?.count || 0,

            user: {
                id: user.id_str,
                username: user.screen_name,
                display_name: user.name,
                followers_count: user.followers_count || 0,
                verified: user.verified || false,
            },

            hashtags: (legacy.entities?.hashtags || []).map(h => h.text),
            mentions: (legacy.entities?.user_mentions || []).map(m => m.screen_name),
        };
    } catch (e) {
        return null;
    }
}

/**
 * Export to JSON
 */
function exportJSON(tweets, filename) {
    fs.writeFileSync(filename, JSON.stringify(tweets, null, 2), 'utf-8');
    console.log(`📁 Exported to ${filename}`);
}

/**
 * Export to CSV
 */
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

/**
 * Print summary
 */
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
        .slice(0, 5)
        .forEach(([lang, count]) => console.log(`     - ${lang}: ${count}`));

    const totalLikes = tweets.reduce((sum, t) => sum + (t.like_count || 0), 0);
    console.log(`   Total Likes: ${totalLikes.toLocaleString()}`);

    if (tweets.length > 0) {
        const top = tweets.reduce((max, t) =>
            (t.like_count || 0) > (max.like_count || 0) ? t : max
        );
        console.log(`\n   🔥 Top Tweet by @${top.user?.username}:`);
        console.log(`      "${top.text?.substring(0, 80)}..."`);
        console.log(`      ❤️ ${top.like_count}`);
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Main
async function main() {
    const args = process.argv.slice(2);
    let keyword = null;
    let count = 100;
    let outputCsv = null;

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
            case '--csv':
                outputCsv = args[++i];
                break;
        }
    }

    if (!keyword) {
        console.log('Usage: node scraper_direct.js -k <keyword> [-c count] [--csv file.csv]');
        console.log('Example: node scraper_direct.js -k "jokowi" -c 100');
        return;
    }

    console.log('🐦 Twitter/X Scraper (Direct Cookie Auth)\n');

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

main().catch(console.error);
