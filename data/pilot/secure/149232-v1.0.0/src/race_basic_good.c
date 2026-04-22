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
const char string[] = "What I want to write";
int fd;

void handler(int curPid)
{
	struct flock lock;
	if (access(fName, W_OK))
			return;
	fd = open(fName, O_WRONLY | O_CREAT | O_EXCL);
	if (fd)
	{
		lock.l_type = F_WRLCK;
		lock.l_whence = SEEK_SET;
		lock.l_start = 0;
		lock.l_len = 0;

		if (fcntl (fd, F_SETLK, &lock) < 0) {
			fprintf (stderr, "Can't lock %s\n", fName);
			exit(EXIT_FAILURE);
		}

		fprintf (stdout, "(%d) Start handler...\n",curPid);
		write(fd, (void *)string, sizeof(char) * 20);
		close(fd);
		fprintf (stdout, "(%d) Stop handler...\n",curPid);
	}
}

int main(int argc, char *argv[])
{
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
