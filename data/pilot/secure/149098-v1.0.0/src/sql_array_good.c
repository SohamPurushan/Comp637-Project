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
#include <mysql.h>
#include <stdio.h>
#include <string.h>



int main(int argc, char *argv[]) 
{
   MYSQL *conn = 0;
   MYSQL_RES *res = 0;
   MYSQL_ROW row ;

   char *server = "localhost";
   char *user = "root";
   char *password = "thisismygoodpassword";
   char *database = "bank";
   
	if (argc < 2)
	{
		printf("You should give an entry parameter!\n");
		return 0;		
	}
	
   conn = mysql_init(NULL);
   
   /* Connect to database */
   if (!mysql_real_connect(conn, server,
         user, password, database, 0, NULL, 0)) {
      fprintf(stderr, "%s\n", mysql_error(conn));
      return 0;
   }

   /* send SQL query */
   char query[512];
   char *fmtString = "SELECT * FROM users WHERE firstname LIKE '%s'";
   unsigned int i = 1;
   for (;i<argc;++i)
   {
	   /* No more buffer overflow */
		if ((strlen(argv[i]) + strlen(fmtString)) > 512){
			printf("The entry is too long...\n");
			break;	
		}
		char param_escaped[512];
		// sanitize the query string
		mysql_real_escape_string(conn, param_escaped, argv[i], strlen(argv[1]));
		sprintf(query,fmtString,param_escaped);
		if (mysql_query(conn, query))
		{
		  fprintf(stderr, "%s\n", mysql_error(conn));
		  return 0;
		}		
		res = mysql_use_result(conn);
		/* output fields 1 and 2 of each row */
		while ((row = mysql_fetch_row(res)) != NULL)
		  printf("%s %s\n", row[1], row[2]);  
	}
   
	/* Release memory used to store results and close connection */
	mysql_free_result(res);
	mysql_close(conn);
	return 0;
}
