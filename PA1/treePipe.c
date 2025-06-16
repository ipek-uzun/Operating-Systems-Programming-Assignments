#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>

void error_exit(const char *msg) {
    perror(msg);
    exit(EXIT_FAILURE);
}

// Function to print indentation based on depth
void print_indent(int depth) {
    for (int i = 0; i < depth; i++) {
         fprintf(stderr, "---");
    }
}


int main(int argc, char *argv[]) {

    if (argc != 4) {
        fprintf(stderr, "Usage: ./treePipe <current depth> <max depth> <left - right>\n");
        exit(EXIT_FAILURE);
    }


    // fd[0]: read
    // fd[1]: write

    int curDepth = atoi(argv[1]);
    int maxDepth = atoi(argv[2]);
    int lr = atoi(argv[3]);
    int num1;

    print_indent(curDepth);
    fprintf(stderr, "> current depth: %d, lr: %d\n", curDepth, lr);

    if (curDepth == 0) {
        fprintf(stderr, "Please enter num1 for the root: ");
        scanf("%d", &num1);
        
    } else {
        // expected to be passed via pipe
        // Non-root nodes: Read num1 from the parent via pipe
        if (scanf("%d", &num1) != 1) {
          error_exit("scanf failed in non-root");
        }

    }

    print_indent(curDepth);
    fprintf(stderr, "> my num1 is: %d\n", num1);
    int num2;

    if (curDepth < maxDepth) {

        int pipe_to_child[2];
        int pipe_from_child[2];
        pipe(pipe_to_child);
        pipe(pipe_from_child);

        int rc = fork();
        if (rc < 0) {
            fprintf(stderr, "fork failed\n");
            exit(1);
        }
        // Left Child process
        if (rc == 0) { 
            

            dup2(pipe_to_child[0], STDIN_FILENO);
            dup2(pipe_from_child[1], STDOUT_FILENO);

            close(pipe_to_child[0]);
            close(pipe_to_child[1]);
            close(pipe_from_child[0]);
            close(pipe_from_child[1]);


            char newDepth[11], newMax[11], newLr[11];
            sprintf(newDepth, "%d", curDepth + 1);
            sprintf(newMax, "%d", maxDepth);
            sprintf(newLr, "%d", 0);  // Always 0 for left child.
            char *args[] = {"./treePipe", newDepth, newMax, newLr, NULL};
            execvp(args[0], args);
            perror("execvp failed in left child");
         }
        
        close(pipe_to_child[0]);
        close(pipe_from_child[1]);

        dprintf(pipe_to_child[1], "%d", num1);
        close(pipe_to_child[1]);
        char buffer1[11];
        int n = read(pipe_from_child[0], buffer1, 10);

        buffer1[n] = '\0';
        num2 = atoi(buffer1);
        close(pipe_from_child[0]);
        wait(NULL);
        print_indent(curDepth);
        fprintf(stderr, "> current depth: %d, lr: %d, my num1: %d, my num2: %d\n",  curDepth, lr, num1, num2);

    } else {
        num2 = 1;
    }

    int pipe_to_target[2], pipe_from_target[2];

    pipe(pipe_to_target);
    pipe(pipe_from_target);
    int rc_target = fork();

    if (rc_target < 0) {
        fprintf(stderr, "Fork failed\n");
            exit(EXIT_FAILURE);
}
    if (rc_target == 0) { // Target program child process:
      
      
      dup2(pipe_to_target[0], STDIN_FILENO);
      dup2(pipe_from_target[1], STDOUT_FILENO);

      close(pipe_to_target[0]); close(pipe_to_target[1]);
      close(pipe_from_target[0]); close(pipe_from_target[1]);
      char *prog = (lr == 0) ? "./left" : "./right";
      char *args[] = {prog, NULL};
      execvp(prog, args);
      perror("execvp failed in target child");
    }

    close(pipe_to_target[0]);
    close(pipe_from_target[1]);
    dprintf(pipe_to_target[1], "%d %d", num1, num2);
    close(pipe_to_target[1]);

    char buffer2[11];
    int m = read(pipe_from_target[0], buffer2, 10);
    buffer2[m] = '\0';
    
    int target_result = atoi(buffer2);
    close(pipe_from_target[0]);
    wait(NULL);

    print_indent(curDepth);
    fprintf(stderr, "> my result is: %d\n", target_result);
    

    // Right subtree
    int final_result;
    if (curDepth < maxDepth) {
        int pipe_to_right[2], pipe_from_right[2];
        pipe(pipe_to_right);
        pipe(pipe_from_right);

        int rc_right = fork();
        if (rc_right < 0) {
            fprintf(stderr, "Fork failed\n");
            exit(EXIT_FAILURE);
        }

        if (rc_right == 0) {
           
            dup2(pipe_to_right[0], STDIN_FILENO);
            dup2(pipe_from_right[1], STDOUT_FILENO);

            close(pipe_to_right[0]); close(pipe_to_right[1]);
            close(pipe_from_right[0]); close(pipe_from_right[1]);

            char newDepth1[11], newMax1[11], newLr1[11];
            sprintf(newDepth1, "%d", curDepth + 1);
            sprintf(newMax1, "%d", maxDepth);
            sprintf(newLr1, "%d", 1);  // Right subtree için lr = 1.
            char *args[] = {"./treePipe", newDepth1, newMax1, newLr1, NULL};
            execvp(args[0], args);
            perror("execvp failed in right child");

        }
        
        close(pipe_to_right[0]);
        close(pipe_from_right[1]);

        dprintf(pipe_to_right[1], "%d", target_result);
        close(pipe_to_right[1]);

        char buffer3[11];
        int k = read(pipe_from_right[0], buffer3, 10);
        buffer3[k] = '\0';
        final_result = atoi(buffer3);
        close(pipe_from_right[0]);
        wait(NULL);
        

        /*
        if (curDepth == 0) {
            printf("The final result is: %d\n", final_result);
        } else {
            dprintf(STDOUT_FILENO, "%d", final_result);
        }
        */
        
         


    } else {
        final_result = target_result;
    }
    if (curDepth == 0)
       fprintf(stderr, "The final result is: %d\n", final_result);
    else
        /* Non-root düğümler, final sonucu ebeveyne iletirler. */
        dprintf(STDOUT_FILENO, "%d", final_result);
    
    
    
    /* else {
        print_indent(curDepth);
        printf("> my result is: %d\n", target_result);
        if (curDepth == 0) {
            print_indent(curDepth);
            printf("The final result is: %d\n", target_result);
        } else {
            dprintf(STDOUT_FILENO, "%d", target_result);
        }
    }
    */


 

    return 0;
}
