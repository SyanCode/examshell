int	ft_iterative_power(int nb, int power)
{
	int result;
	int i;

	if (power < 0)
		return (0);
	result = 1;
	i = 0;
	while (i < power)
	{
		result = result * nb;
		i++;
	}
	return (result);
}
