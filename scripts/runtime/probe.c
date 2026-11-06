/* Positive controls: injection must observe every selected API before use. */
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <spawn.h>
#include <netdb.h>
#include <errno.h>
#include <string.h>
#include <dlfcn.h>
int main(int argc,char **argv) {
    char *args[]={(char*)"true",0};char *env[]={0};pid_t child;
    if (argc>1 && strcmp(argv[1],"sandbox")==0) {
        int fd=socket(AF_INET,SOCK_STREAM,0);
        struct sockaddr_in a={0};a.sin_family=AF_INET;a.sin_port=htons(9);a.sin_addr.s_addr=htonl(0x7f000001);
        int result=connect(fd,(struct sockaddr*)&a,sizeof(a));int blocked=result<0 && errno==EPERM;
        if(fd>=0)close(fd);
        pid_t p=fork();if(p==0)_exit(90);
        return blocked && p<0 && errno==EPERM ? 0:1;
    }
    int (*active)(void) = (int (*)(void))dlsym(RTLD_DEFAULT,"veilguard_guard_active");
    if (!active || active()!=1) return 93;
    socket(AF_INET,SOCK_STREAM,0); connect(-1,0,0);sendto(-1,0,0,0,0,0);
    struct addrinfo *r=0;getaddrinfo("127.0.0.1",0,0,&r);
    if(fork()==0)_exit(91);if(vfork()==0)_exit(92);
    posix_spawn(&child,"/bin/true",0,0,args,env);posix_spawnp(&child,"true",0,0,args,env);
    execve("/bin/true",args,env);
    return 0;
}
