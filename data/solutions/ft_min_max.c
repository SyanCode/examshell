void	ft_min_max(int a, int b, int c, int d, int *min, int *max)
{
	int values[4];
	int i;
	int mn;
	int mx;

	values[0] = a;
	values[1] = b;
	values[2] = c;
	values[3] = d;
	mn = values[0];
	mx = values[0];
	i = 1;
	while (i < 4)
	{
		if (values[i] < mn)
			mn = values[i];
		if (values[i] > mx)
			mx = values[i];
		i++;
	}
	*min = mn;
	*max = mx;
}
