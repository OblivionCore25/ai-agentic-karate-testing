package karate;

import com.intuit.karate.junit5.Karate;

class KarateRunner {
    
    @Karate.Test
    Karate testAll() {
        return Karate.run().relativeTo(getClass());
    }
    
    @Karate.Test
    Karate testGenerated() {
        return Karate.run("generated").relativeTo(getClass());
    }
}
