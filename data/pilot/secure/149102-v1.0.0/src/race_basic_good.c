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
	if (access(fName, W_OK))
			return;	
	fd = open(fName, O_WRONLY | O_CREAT | O_EXCL);
	if (fd)
	{		
		fprintf (stdout, "(%d) Start handler...\n",curPid);
		write(fd, (void *)string, sizeof(char) * 20);
		close(fd);
		fprintf (stdout, "(%d) Stop handler...\n",curPid);
	}
}

FILE *safe_open_wplus(char *fname)
{
	struct stat lstat_info, fstat_info;
	FILE *fp; char *mode = "rb+"; /*We perform our own truncation.*/
	int fd;
	if(lstat(fname, &lstat_info) == –1)
	{
		/* If the lstat() failed for reasons other than the file
		  not existing, return 0, specifying error. */
		if( errno != ENOENT ) { return 0; }
		if((fd = open(fname, O_CREAT|O_EXCL| O_RDWR, 0600)) == –1) { 
			return 0; } mode = "wb"; 
	}
	else 
	{
		/* Open an existing file */
		if((fd = open(fname, O_RDWR)) == –1) { return 0; }
		if(fstat(fd, &fstat_info) == –1 || 
		lstat_info.st_mode != fstat_info.st_mode || 
		lstat_info.st_ino != fstat_info.st_ino || 
		lstat_info.st_dev != fstat_info.st_dev ) 
		{
			close(fd);
			return 0; 
		}
		/* Turn the file into an empty file, to mimic w+ semantics. */
		ftruncate(fd, 0);
	} 
	/* Open an stdio file over the low-level one */ 
	fp = fdopen(fd, mode); if(!fp) {
	close(fd); unlink(fname); return 0;
	}
	return fp;
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
