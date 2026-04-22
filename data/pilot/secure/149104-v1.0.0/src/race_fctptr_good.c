/* This software was developed at the National Institute of Standards and
 * Technology by employees of the Federal Government in the course of their
 * official duties. Pursuant to title 17 Section 105 of the United States
 * Code this software is not subject to copyright protection and is in the
 * public domain. NIST assumes no responsibility whatsoever for its use by
 * other parties, and makes no guarantees, expressed or implied, about its
 * quality, reliability, or any other characteristic.

 * We would appreciate acknowledgement if the software is used.
 * The SAMATE project website is: http://samate.nist.gov
*/
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>

const char fName[] = "test.file";
const char string1[] = "What I want to write _ fct1";
const char string2[] = "What I want to write _ fct2";
int fd;

typedef void (*fctPtr)(void);
fctPtr myFunctions[2];


void fct1(void) {
	fprintf(stdout, "call fct1\n");
	write(fd, (void *)string1, 20*sizeof(char));
}

void fct2(void) {
	fprintf(stdout, "call fct2\n");
	write(fd, (void *)string2, 20*sizeof(char));
}

void handler(int curPid)
{
	if (access(fName, W_OK))
			return;	
	fd = open(fName, O_WRONLY | O_CREAT | O_EXCL);
	if (fd)
	{		
		fprintf (stdout, "(%d) Start handler...\n",curPid);
		unsigned int i = rand() % 2;
		myFunctions[i]();
		close(fd);
		fprintf (stdout, "(%d) Stop handler...\n",curPid);
	}
}

int main(int argc, char *argv[])
{
	myFunctions[0] = fct1;
	myFunctions[1] = fct2;
	
	pid_t pid = 0;
	// create fork 1
	if (fork())
		return 0;
	
	for (unsigned i=0;i<3;++i) {
		pid = fork();
		if (pid)
		{
			printf ("Run: %d\n",pid);
			handler(pid);
		}
	}
	return 0;
}
