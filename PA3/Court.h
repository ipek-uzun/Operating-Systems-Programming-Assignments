#ifndef COURT_H
#define COURT_H

#include <semaphore.h>
#include <pthread.h>
#include <cstdio>
#include <stdexcept>

class Court {
private:
    int  neededPlayers;      
    int  hasReferee;         // 0 / 1
    int  capacity;           
    int  inside;             
    bool matchGoing;         
    pthread_t refereeId;     

    sem_t court_available;   
	sem_t matchStart;
    sem_t match_end;         
    pthread_barrier_t barrier; 
    pthread_mutex_t mutex;   

public:
// Constructor — initializes all variables and synchronization primitives
    Court(int playersPerMatch, int refereePresent) {
        if (playersPerMatch <= 0)
            throw std::invalid_argument("An error occurred.");
        if (refereePresent != 0 && refereePresent != 1)
            throw std::invalid_argument("An error occurred.");

        neededPlayers = playersPerMatch;
        hasReferee    = refereePresent;
        capacity      = neededPlayers + hasReferee;
        inside        = 0;
        matchGoing    = false;
        refereeId     = 0;
	sem_init(&matchStart, 0, 0);
        sem_init(&court_available, 0, capacity);
        sem_init(&match_end,      0, 0);
        pthread_barrier_init(&barrier, nullptr, capacity);
        pthread_mutex_init(&mutex, nullptr);
    }
 // Destructor — cleans up all synchronization primitives
    ~Court() {
        sem_destroy(&court_available);
        sem_destroy(&match_end);
        pthread_barrier_destroy(&barrier);
        pthread_mutex_destroy(&mutex);
	sem_destroy(&matchStart);
    }

// Player (or referee) enters the court
void enter() {
    unsigned long tid = (unsigned long)pthread_self();
    printf("Thread ID: %lu, I have arrived at the court.\n", tid);

while (true) {
        sem_wait(&court_available);      //  Wait for a slot to become available

        pthread_mutex_lock(&mutex);
        if (matchGoing) {                //If a match is ongoing, release token and wait for match to end
            pthread_mutex_unlock(&mutex);
            sem_post(&court_available);  
            sem_wait(&match_end);        
            continue;                    
        }

          // Safe to enter — update state
        inside++;

        bool formed = false;
        if ((!hasReferee && inside == neededPlayers) ||
            ( hasReferee && inside == capacity)) {
// Form the match when enough players (and referee, if needed) are present           
 matchGoing = true;
            formed     = true;
            if (hasReferee)
                refereeId = pthread_self();    // The last entrant becomes the referee
        }
        int snapshot = inside;
//        pthread_mutex_unlock(&mutex);
// Print status while still holding mutex to maintain print-order consistency
        if (formed) {
            printf("Thread ID: %lu, There are enough players, starting a match.\n", tid);
        } else {
            printf("Thread ID: %lu, There are only %d players, passing some time.\n",
                   tid, snapshot);
        }
	pthread_mutex_unlock(&mutex);
        break;                          
    }
}

    //  play() will be implemented in cpp
    void play();

// Player or referee leaves the court
    void leave() {
        unsigned long tid = (unsigned long)pthread_self();

        pthread_mutex_lock(&mutex);
        bool playing = matchGoing;
        pthread_mutex_unlock(&mutex);
 // If no match was formed, the player simply leaves
        if (!playing) {
            printf("Thread ID: %lu, I was not able to find a match and I have to leave.\n", tid);

            pthread_mutex_lock(&mutex);
            inside--;
            pthread_mutex_unlock(&mutex);

            sem_post(&court_available);   // Release the slot
            return;
        }
 // Wait for all match participants at the barrier
        pthread_barrier_wait(&barrier);    

        if (hasReferee && pthread_equal(pthread_self(), refereeId)) {
  // Referee announces end of the match
            printf("Thread ID: %lu, I am the referee and now, match is over. I am leaving.\n", tid);
            for (int i = 0; i < neededPlayers; ++i)
                sem_post(&match_end);     // wake up all players
        } else {

 // Players wait for the referee's signal before leaving
            if (hasReferee)
                sem_wait(&match_end);
            printf("Thread ID: %lu, I am a player and now, I am leaving.\n", tid);
        }
 // Update state and check if court is now empty
        pthread_mutex_lock(&mutex);
        inside--;
        bool last = (inside == 0);
        pthread_mutex_unlock(&mutex);

        if (last) {
 // Last person resets the court for the next match
            pthread_mutex_lock(&mutex);
            matchGoing = false;
            refereeId  = 0;
            pthread_mutex_unlock(&mutex);

            printf("Thread ID: %lu, everybody left, letting any waiting people know.\n", tid);
 // Open slots for the next round of players
            for (int i = 0; i < capacity; ++i)
                sem_post(&court_available);
        }
    }
};

#endif // COURT_H
