/* The following code is wrapper around the UNIX command cat which prints the
contents of a file to standard out. It is also injectable:
*/

#include <stdio.h>
#include <unistd.h>
int main(int argc, char **argv) {
char cat[] = "cat ";
char *command;
size_t commandLength;
commandLength = strlen(cat) + strlen(argv[1]) + 1;
command = (char *) malloc(commandLength);
strncpy(command, cat, commandLength);
strncat(command, argv[1], (commandLength - strlen(cat)) );
system(command);
return (0);
}



/* Used normally, the output is simply the contents of the file requested:

$ ./catWrapper Story.txt
When last we left our heroes...

However, if we add a semicolon and another command to the end of this line,
the command is executed by catWrapper with no complaint:

$ ./catWrapper Story.txt; ls
When last we left our heroes...
Story.txt doubFree.c nullpointer.c
unstosig.c www* a.out*
format.c strlen.c useFree*
catWrapper* misnull.c strlength.
c useFree.c commandinjection.c
nodefault.c trunc.c writeWhatWhere.c

If catWrapper had been set to have a higher privilege level than the standard
user, arbitrary commands could be executed with that higher privilege
*/