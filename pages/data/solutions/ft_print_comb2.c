#include <unistd.h>

int	main(void)
{
	int n;
	char buf[2];

	n = 0;
	while (n <= 99)
	{
		buf[0] = (n / 10) + '0';
		buf[1] = (n % 10) + '0';
		write(1, buf, 2);
		if (n != 99)
			write(1, ", ", 2);
		n++;
	}
	write(1, "\n", 1);
	return (0);
}
