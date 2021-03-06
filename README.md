
simple console app to work with virtual file system, based on sqlite database

***

#### Description:

##### RUS:

Основные нюансы реализации:

1. 	Для предоставления иерархии папок служит таблица-связка **FoldersTree**.
	На данный момент она хранит только связи между родителем и прямым потомком (подпапкой).
	Обход иерархии папок происходит рекурсивно, что пораждает множество запросов
	к базе данных при выполнении, например, команды list.
	Однако, изначальное моделирование данных через таблицу-свяку позволит, при необходимости,
	наполить таблицу-связку данными о более высоких уровнях иерархии, и более оптимально производить запросы, вытаскивая иерархию целиком, за один запрос.

2.	В зависимости от аргументов коммандной строки выполняется определенный класс-команда.

3.	Менеджеры контекста при работе с БД позволяют следовать ACID принципам, упрощают код 
	и позволяют не переживать за возможные сбои при работе с БД.

4.	Общая функциоальность при работе с БД вынесена в специальный mixin класс, который можно
	переиспользовать в классах команд.

5.	В данный момент реализована логика для команд list, add_folder, add_file, remove, show, edit.
	Все реализовано.


###### Планы по доработкам:


1. То как сейчас работает логика в команде `list` - не правильно! Нужно воспользоваться всеми преимуществами таблицы-связки,
	тем самым появится возможность считать размер любой директории с меньшим числом запросов в базу, даже средствами самого SQL.

2. Заменить форматирование через %s и %d на более безопасные аналоги, предоставляемые интерфейсами БД.

3. Почистить код от артефактов отладки и других вещей не по делу.

4. Дописать обработку ошибок пользователя, где её нет.


##### ENG:

`In progress.`