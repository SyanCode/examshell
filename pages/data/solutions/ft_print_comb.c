#include <unistd.h>

int	main(void)
{
	int a;
	int b;
	int c;
	char buf[3];

	a = 0;
	while (a <= 7)
	{
		b = a + 1;
		while (b <= 8)
		{
			c = b + 1;
			while (c <= 9)
			{
				buf[0] = a + '0';
				buf[1] = b + '0';
				buf[2] = c + '0';
				write(1, buf, 3);
				if (!(a == 7 && b == 8 && c == 9))
					write(1, ", ", 2);
				c++;
			}
			b++;
		}
		a++;
	}
	write(1, "\n", 1);
	return (0);
}
