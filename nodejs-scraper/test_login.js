import { Scraper } from '@the-convocation/twitter-scraper';

async function test() {
    console.log('🐦 Testing @the-convocation/twitter-scraper...\n');
    const scraper = new Scraper();

    try {
        console.log('🔑 Logging in...');
        await scraper.login('feiscrap', '@Fairnanda049#');
        console.log('✅ Login SUCCESS!\n');

        // Try search
        console.log('🔍 Searching for "indonesia"...');
        const tweets = [];
        const results = scraper.searchTweets('indonesia', 10, 0);

        for await (const tweet of results) {
            tweets.push({
                text: tweet.text,
                username: tweet.username,
                likes: tweet.likes
            });
            console.log(`   Found: @${tweet.username}: ${tweet.text?.substring(0, 40)}...`);
            if (tweets.length >= 10) break;
        }

        console.log(`\n✅ Total tweets: ${tweets.length}`);

    } catch (e) {
        console.log('❌ Error:', e.message);
        if (e.message.includes('Login')) {
            console.log('\n💡 Tips:');
            console.log('   - Check username and password');
            console.log('   - Twitter might require email verification');
            console.log('   - Account might be locked due to suspicious activity');
        }
    }
}

test();
